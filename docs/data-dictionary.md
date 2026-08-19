# Full-data dictionary

Status: M7 verified source schema plus M8 verified typed semantic view. Source values remain restricted and source-faithful; casts and applicability rules live only in the restricted metric database.

Official sources:

- [CRT Reference Pool Disclosure File Layouts v4.2](https://capitalmarkets.freddiemac.com/crt/docs/pdfs/crt-reference-pool-disclosure-file-layouts.pdf), effective July 2026.
- [CRT Reference Pool Glossary v4.2](https://capitalmarkets.freddiemac.com/crt/docs/pdfs/crt-reference-pool-glossary.pdf), effective July 2026.

## Storage columns

Every Parquet row begins with three lineage columns:

| Column | Meaning |
| --- | --- |
| `deal_id` | Deal derived from the validated standard monthly member name |
| `source_member` | Exact ZIP member from which the row was read |
| `source_field_count` | Original row width: 89, 90, or 93 |

The remaining columns map positionally to the official headerless layout:

| Pos. | Normalized column | Official attribute | Family / applicability |
| ---: | --- | --- | --- |
| 1 | `period` | Period | Reporting key; all pools |
| 2 | `reference_pool_number` | Reference Pool Number | Pool key; all pools |
| 3 | `loan_identifier` | Loan Identifier | Restricted row key; never public |
| 4 | `amortization_type` | Amortization Type | Origination/product |
| 5 | `seller_name` | Seller Name | Organization; private first release |
| 6 | `property_state` | Property State | Geography; aggregate use requires approval |
| 7 | `postal_code_3_digit` | Postal Code (3-Digit) | Geography; aggregate use requires approval |
| 8 | `metropolitan_statistical_area_or_division` | MSA or Metropolitan Division | Geography; aggregate use requires approval |
| 9 | `first_payment_date` | First Payment Date | Origination/vintage |
| 10 | `maturity_date` | Maturity Date | Term/maturity |
| 11 | `original_loan_term` | Original Loan Term | Origination/product |
| 12 | `original_interest_rate` | Original Interest Rate | Origination/rate |
| 13 | `original_upb` | Original UPB | Origination/exposure |
| 14 | `upb_at_issuance` | UPB at Issuance | Issuance/exposure |
| 15 | `loan_purpose` | Loan Purpose | Origination/cohort |
| 16 | `channel` | Channel | Origination/cohort |
| 17 | `property_type` | Property Type | Collateral/cohort |
| 18 | `number_of_units` | Number of Units | Collateral/cohort |
| 19 | `occupancy_status` | Occupancy Status | Collateral/cohort |
| 20 | `number_of_borrowers` | Number of Borrowers | Origination/cohort; never row-level public |
| 21 | `first_time_homebuyer_indicator` | First Time Homebuyer Indicator | Origination/cohort |
| 22 | `prepayment_penalty_indicator` | Prepayment Penalty Indicator | Origination/product |
| 23 | `classic_fico` | Classic FICO | Credit attribute; restricted and aggregate-only after approval |
| 24 | `original_ltv` | Original Loan-To-Value | Credit/collateral attribute |
| 25 | `original_cltv` | Original Combined Loan-To-Value | Credit/collateral attribute |
| 26 | `original_dti` | Original Debt-To-Income | Credit attribute |
| 27 | `mortgage_insurance_percent` | Mortgage Insurance Percent | Credit enhancement |
| 28 | `updated_credit_score_at_issuance` | Updated Credit Score at Issuance | Select pools; terms-gated |
| 29 | `special_eligibility_program` | Special Eligibility Program | Program/cohort |
| 30 | `mortgage_insurance_type` | Mortgage Insurance Type | Actual Loss pools only |
| 31 | `filler_31` | Filler | Reserved; preserve null/source value |
| 32 | `disaster_grace_period` | Disaster Grace Period | Select Fixed Severity pools |
| 33 | `servicer_name` | Servicer Name | Organization; private first release |
| 34 | `loan_age` | Loan Age | Current performance/cohort |
| 35 | `remaining_months_to_legal_maturity` | Remaining Months to Legal Maturity | Current term |
| 36 | `adjusted_remaining_months_to_maturity` | Adjusted Remaining Months to Maturity | Current term |
| 37 | `current_loan_delinquency_status` | Current Loan Delinquency Status | Current performance |
| 38 | `payment_history` | Payment History | Restricted 24-month row history; never public |
| 39 | `current_interest_rate` | Current Interest Rate | Current performance/rate |
| 40 | `current_actual_upb` | Current Actual UPB | Current exposure |
| 41 | `current_interest_bearing_upb` | Current Interest Bearing UPB | Current exposure |
| 42 | `upb_at_removal` | UPB at Time of Removal | Exit exposure |
| 43 | `zero_balance_code` | Zero Balance Code | Exit/outcome; construct- and period-aware |
| 44 | `zero_balance_effective_date` | Zero Balance Effective Date | Exit/outcome |
| 45 | `defect_settlement_date` | Underwriting Defect and Major Servicing Defect Settlement Date | Defect/settlement |
| 46 | `modification_flag` | Modification Flag | Modification state |
| 47 | `delinquency_due_to_disaster` | Delinquency Due to Disaster | Disaster/assistance |
| 48 | `ddlpi` | Due Date of Last Paid Installment | Current performance |
| 49 | `bankruptcy_flag` | Bankruptcy Flag | Actual Loss pools only |
| 50 | `foreclosure_referral_date` | Date Referred to Foreclosure | Actual Loss pools only |
| 51 | `net_sales_proceeds` | Net Sales Proceeds | Actual Loss pools only |
| 52 | `mi_credit` | MI Credit | Actual Loss pools only |
| 53 | `taxes_and_insurance` | Taxes and Insurance | Actual Loss pools only |
| 54 | `legal_costs` | Legal Costs | Actual Loss pools only |
| 55 | `maintenance_and_preservation_costs` | Maintenance and Preservation Costs | Actual Loss pools only |
| 56 | `bankruptcy_cramdown_costs` | Bankruptcy Cramdown Costs | Actual Loss pools only |
| 57 | `miscellaneous_expenses` | Miscellaneous Expenses | Actual Loss pools only |
| 58 | `miscellaneous_credits` | Miscellaneous Credits | Actual Loss pools only |
| 59 | `mi_cancellation_indicator` | Mortgage Insurance Cancellation Indicator | Mortgage insurance |
| 60 | `estimated_ltv` | Estimated Loan-To-Value (Monthly) | Current collateral attribute |
| 61 | `filler_61` | Filler | Former FSD position; preserve null/source value |
| 62 | `updated_credit_score_1` | Updated Credit Score #1 – Quarterly | Terms-gated; public use not approved |
| 63 | `updated_credit_score_2` | Updated Credit Score #2 – Quarterly | Terms-gated; public use not approved |
| 64 | `number_of_modifications` | Number of Modifications | Modification history |
| 65 | `modification_program` | Modification Program | Modification history |
| 66 | `modification_type` | Modification Type | Modification history |
| 67 | `modification_first_payment_date` | Modification First Payment Date | Modification history |
| 68 | `modification_dti` | Modification Debt-To-Income | Modification/credit attribute |
| 69 | `total_capitalized_amount` | Total Capitalized Amount | Modification outcome |
| 70 | `interest_rate_step_indicator` | Interest Rate Step Indicator | Modification terms |
| 71 | `first_step_rate_adjustment_date` | First Step Rate Adjustment Date | Modification terms |
| 72 | `first_step_rate` | First Step Rate | Modification terms |
| 73 | `second_step_rate_adjustment_date` | Second Step Rate Adjustment Date | Modification terms |
| 74 | `second_step_rate` | Second Step Rate | Modification terms |
| 75 | `third_step_rate_adjustment_date` | Third Step Rate Adjustment Date | Modification terms |
| 76 | `third_step_rate` | Third Step Rate | Modification terms |
| 77 | `fourth_step_rate_adjustment_date` | Fourth Step Rate Adjustment Date | Modification terms |
| 78 | `fourth_step_rate` | Fourth Step Rate | Modification terms |
| 79 | `fifth_step_rate_adjustment_date` | Fifth Step Rate Adjustment Date | Modification terms |
| 80 | `fifth_step_rate` | Fifth Step Rate | Modification terms |
| 81 | `delinquent_accrued_interest` | Delinquent Accrued Interest | Actual Loss pools only |
| 82 | `current_period_modification_costs` | Current Period Modification Costs | Actual Loss pools only; renamed July 2026 |
| 83 | `updated_credit_score_3` | Updated Credit Score #3 – Quarterly | Reserved for future use |
| 84 | `property_valuation_method` | Property Valuation Method | Collateral/origination |
| 85 | `group_number` | Group Number | Pool grouping |
| 86 | `enhanced_relief_refi_indicator` | Enhanced Relief Refi Indicator | Actual Loss pools only |
| 87 | `borrower_assistance_plan` | Borrower Assistance Plan | Assistance state |
| 88 | `payment_deferral_flag` | Payment Deferral Flag | Assistance state |
| 89 | `distressed_principal_balance_flag` | Distressed Principal Balance Flag | Actual Loss pools only |
| 90 | `temporary_subsidy_buydown_plan_type` | Temporary Subsidy Buydown Plan Type | September 2024 onward |
| 91 | `vantagescore_4` | VantageScore 4.0 | July 2026 onward; terms-gated |
| 92 | `actual_loss` | Actual Loss | Actual Loss pools, July 2026 onward |
| 93 | `cumulative_modification_costs` | Cumulative Modification Costs | Actual Loss pools, July 2026 onward |

## Version and sentinel rules

- The source is headerless and positional. M7 accepts only 89, 90, or 93 fields and fails closed for any other width.
- Observed mappings are 89 fields for 2023-07–2024-08, 90 fields for 2024-09–2026-06, and 93 fields for 2026-07. Missing trailing positions are stored as null; positions are never shifted.
- Empty source attributes become null. Non-empty source values remain strings in M7 so codes such as `RA`, `XX`, `999`, `9999`, `7`, `9`, `99`, and period-specific enumerations cannot be silently coerced.
- `999` and `9999` commonly represent unavailable numeric credit/ratio values; they are not numeric observations. M8 applies field-specific v4.2 glossary rules in the typed view.
- Zero Balance Code meanings vary by Fixed Severity versus Actual Loss construct and changed for Actual Loss reporting in July 2026. M8 uses construct- and period-aware mappings.
- Updated credit-score fields are retained under the approved private authorization but remain terms-gated and excluded from the first public cohort set.
- All row-level columns are restricted. Public use requires an explicitly approved aggregate projection; loan identifiers and payment histories are never public.

## M8 typed semantic rules

Metric version `m8.1.0` creates `loan_period_typed` without rewriting the M7 Parquet files:

- Current Actual UPB, issuance/removal balances, Actual Loss, modification costs, rates, and ratio attributes use fail-safe `try_cast` operations.
- Numeric delinquency states map 0=current, 1=D30, 2=D60, and 3+=D90+; `RA` maps to REO and `XX` to unknown. REO/unknown UPB is excluded from analytical delinquency denominators and retained as explicit evidence.
- Active eligibility requires positive Current Actual UPB, no Zero Balance Code, and a numeric delinquency state.
- Classic FICO accepts 300–850; LTV/CLTV accept 1–998 excluding sentinel 999; DTI accepts 1–65 excluding 999. Unknown values are never imputed.
- The observed HQA population maps to the Actual Loss construct because Distressed Principal Balance Flag is applicable (`Y`/`N`) on every source row; no unknown construct was observed.
- Actual Loss zero-balance codes before July 2026 and from July 2026 onward use the official period-specific mappings. Code 01 is voluntary payoff; applicable credit-event codes remain separate from defect, RPL-sale, other, and termination codes.
- Risk layers count four transparent conditions: Classic FICO <680, original LTV >90, original DTI >45, and second-home/investment occupancy. The count is descriptive, restricted, and not a borrower score.

## M9 private workbench projection

The private loan-detail endpoint returns an explicit restricted analytical subset from `loan_period_typed`: masked or affirmatively revealed loan identifier, reference pool, current UPB, performance state, zero-balance code, risk-layer count, valid Classic FICO/LTV/CLTV/DTI/coupon/age values, vintage, purpose, channel, occupancy, property type/state, modification, assistance/deferral/disaster indicators, servicer, and pool construct.

All fields remain restricted-derived analytics. The browser translates documented loan-purpose, occupancy, modification, assistance, and deferral codes into plain language without changing source values. Identifiers are masked by default. The M9 evidence package intentionally excludes the entire row subset and every identifier.
- Updated credit scores and VantageScore 4.0 remain retained but unused because their terms-specific product use is not approved.
