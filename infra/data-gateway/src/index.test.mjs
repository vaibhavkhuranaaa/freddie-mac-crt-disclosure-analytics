import assert from "node:assert/strict";
import test from "node:test";

import { fetchPartition } from "./index.mjs";

const url =
  "https://data.internal/full-data-v2026-07/2022-HQA1--202607.parquet";

function environment(object = null) {
  const keys = [];
  return {
    env: {
      DATA_GATEWAY_TOKEN: "test-token",
      CRT_DATA: {
        async get(key) {
          keys.push(key);
          return object;
        },
      },
    },
    keys,
  };
}

test("rejects anonymous and invalid requests before reading R2", async () => {
  const { env, keys } = environment();
  assert.equal((await fetchPartition(new Request(url), env)).status, 401);
  assert.equal(
    (
      await fetchPartition(
        new Request(url, {
          headers: { Authorization: "Bearer test-token-extra" },
        }),
        env,
      )
    ).status,
    401,
  );
  assert.equal(
    (
      await fetchPartition(
        new Request(url.replace("2022-HQA1", "../../private"), {
          headers: { Authorization: "Bearer test-token" },
        }),
        env,
      )
    ).status,
    404,
  );
  assert.deepEqual(keys, []);
});

test("fails closed without a configured secret and rejects writes", async () => {
  const { env, keys } = environment();
  delete env.DATA_GATEWAY_TOKEN;
  assert.equal(
    (
      await fetchPartition(
        new Request(url, {
          headers: { Authorization: "Bearer undefined" },
        }),
        env,
      )
    ).status,
    401,
  );
  assert.equal(
    (
      await fetchPartition(
        new Request(url, {
          method: "POST",
          headers: { Authorization: "Bearer test-token" },
        }),
        env,
      )
    ).status,
    405,
  );
  assert.deepEqual(keys, []);
});

test("reads only the exact release object for an authenticated GET", async () => {
  const object = {
    body: "parquet-bytes",
    size: 13,
    httpEtag: '"fixture"',
  };
  const { env, keys } = environment(object);
  const result = await fetchPartition(
    new Request(url, { headers: { Authorization: "Bearer test-token" } }),
    env,
  );
  assert.equal(result.status, 200);
  assert.equal(
    result.headers.get("Content-Type"),
    "application/vnd.apache.parquet",
  );
  assert.equal(await result.text(), "parquet-bytes");
  assert.deepEqual(keys, [
    "full-data-v2026-07/2022-HQA1--202607.parquet",
  ]);
});

test("does not list the bucket or reveal missing objects", async () => {
  const { env } = environment();
  const result = await fetchPartition(
    new Request(url, { headers: { Authorization: "Bearer test-token" } }),
    env,
  );
  assert.equal(result.status, 404);
  assert.equal(await result.text(), "Not found.");
});
