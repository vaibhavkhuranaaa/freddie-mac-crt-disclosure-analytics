const RELEASE = "full-data-v2026-07";
const ASSET = /^[0-9]{4}-HQA[0-9]--20[0-9]{4}\.parquet$/;

function response(status, message, headers = {}) {
  return new Response(message, {
    status,
    headers: {
      "Cache-Control": "private, no-store",
      "Content-Type": "text/plain; charset=utf-8",
      "X-Content-Type-Options": "nosniff",
      ...headers,
    },
  });
}

async function verifyToken(provided, expected) {
  if (typeof expected !== "string" || expected.length === 0) {
    return false;
  }
  const encoder = new TextEncoder();
  const [providedHash, expectedHash] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(provided ?? "")),
    crypto.subtle.digest("SHA-256", encoder.encode(`Bearer ${expected}`)),
  ]);
  if (typeof crypto.subtle.timingSafeEqual === "function") {
    return crypto.subtle.timingSafeEqual(providedHash, expectedHash);
  }

  // Node's Web Crypto test runtime does not yet expose timingSafeEqual.
  const providedBytes = new Uint8Array(providedHash);
  const expectedBytes = new Uint8Array(expectedHash);
  let difference = 0;
  for (let index = 0; index < providedBytes.length; index += 1) {
    difference |= providedBytes[index] ^ expectedBytes[index];
  }
  return difference === 0;
}

export async function fetchPartition(request, env) {
  const path = new URL(request.url).pathname;
  try {
    if (request.method !== "GET") {
      return response(405, "Method not allowed.", { Allow: "GET" });
    }
    if (
      !(await verifyToken(
        request.headers.get("Authorization"),
        env.DATA_GATEWAY_TOKEN,
      ))
    ) {
      return response(401, "Unauthorized.");
    }

    const prefix = `/${RELEASE}/`;
    const asset = path.startsWith(prefix) ? path.slice(prefix.length) : "";
    if (!ASSET.test(asset)) {
      return response(404, "Not found.");
    }

    const object = await env.CRT_DATA.get(`${RELEASE}/${asset}`);
    if (!object) {
      return response(404, "Not found.");
    }
    return new Response(object.body, {
      headers: {
        "Cache-Control": "private, no-store",
        "Content-Length": String(object.size),
        "Content-Type": "application/vnd.apache.parquet",
        ETag: object.httpEtag,
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch (error) {
    console.error(
      JSON.stringify({
        message: "gateway request failed",
        error: error instanceof Error ? error.message : String(error),
        method: request.method,
        path,
      }),
    );
    return response(500, "Internal server error.");
  }
}

export default { fetch: fetchPartition };
