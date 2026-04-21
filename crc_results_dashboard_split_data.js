window.CRC_SPLIT_DASHBOARD_DATA = {
    "run_id":  "20260420_crc_split_v2",
    "generated_at":  "2026-04-21 15:58:33",
    "baseline_integrated_crc":  {
                                    "run_id":  "20260418_crc_v1",
                                    "features_rows":  6675,
                                    "features_cols":  18288,
                                    "labels_rows":  6675,
                                    "labels_unique_samples":  46,
                                    "labels_unique_drugs":  295,
                                    "join_rate_samples":  0.53238156005742543,
                                    "pair_rows":  6675
                                },
    "master_table":  {
                         "path":  "runs\\20260420_crc_split_v2\\raw_meta\\master_cellline_cohort_table.csv",
                         "rows":  46,
                         "cohort_counts":  {
                                               "colon":  39,
                                               "rectal":  5,
                                               "unknown":  2
                                           }
                     },
    "cohorts":  {
                    "colon":  {
                                  "cohort":  "colon",
                                  "split_counts":  {
                                                       "label_before":  12538,
                                                       "label_after":  10598,
                                                       "sample_before":  20443404,
                                                       "sample_after":  354552,
                                                       "drug_before":  295,
                                                       "drug_after":  295,
                                                       "lincs_before":  101,
                                                       "lincs_after":  101,
                                                       "target_before":  485,
                                                       "target_after":  485
                                                   },
                                  "features":  {
                                                   "rows":  5576,
                                                   "cols":  17920
                                               },
                                  "labels":  {
                                                 "rows":  5576,
                                                 "unique_samples":  20,
                                                 "unique_drugs":  295
                                             },
                                  "pair_features":  {
                                                        "pairs":  5576,
                                                        "pair_features_newfe_rows":  5576,
                                                        "pair_features_newfe_v2_rows":  5576
                                                    },
                                  "chem_qc":  {
                                                  "drug_rows":  295,
                                                  "invalid_smiles_count":  295,
                                                  "invalid_smiles_ratio":  1.0,
                                                  "rdkit_enabled":  false,
                                                  "rdkit_error":  "rdkit_disabled_for_stability_in_current_runtime",
                                                  "chem_fallback_mode":  "all_zero_morgan_and_nan_descriptors_then_final_numeric_fillna_zero"
                                              },
                                  "pipeline":  {
                                                   "ml_ok_count":  0,
                                                   "dl_ok_count":  0,
                                                   "graph_ok_count":  0,
                                                   "ml_skipped_reason":  "start_at_post_step4",
                                                   "dl_skipped_reason":  "start_at_post_step4",
                                                   "graph_skipped_reason":  "start_at_post_step4",
                                                   "ml_results_exists":  true,
                                                   "dl_results_exists":  true,
                                                   "graph_results_exists":  true,
                                                   "ensemble_ok":  true,
                                                   "step6_ok":  true,
                                                   "step7_ok":  true,
                                                   "ensemble_error":  null,
                                                   "step6_error":  null,
                                                   "step7_error":  null,
                                                   "run_mode":  "full"
                                               },
                                  "ensemble":  {
                                                   "n_models":  6,
                                                   "spearman":  0.56396214974424164,
                                                   "rmse":  2.2226494658423546,
                                                   "pearson":  0.60236765139301784,
                                                   "r2":  0.35352344421978177,
                                                   "weights":  {
                                                                   "CatBoost":  0.19470120127363327,
                                                                   "LightGBM":  0.1840521706370514,
                                                                   "XGBoost":  0.18993873634511832,
                                                                   "FlatMLP":  0.12718194144202577,
                                                                   "ResidualMLP":  0.14059057586382584,
                                                                   "Cross-Attention":  0.16353537443834534
                                                               }
                                               },
                                  "step6":  {
                                                "type":  "TCGA-COAD + GSE39582",
                                                "top15_count":  15,
                                                "target_expressed":  "29/30",
                                                "precision_at_15":  0.13333333333333333,
                                                "precision_at_20":  0.2
                                            },
                                  "step7":  {
                                                "n_assays":  22,
                                                "n_input":  15,
                                                "n_output":  15,
                                                "candidate_count":  15,
                                                "approved_count":  0,
                                                "top5":  [
                                                             {
                                                                 "final_rank":  "1",
                                                                 "drug_name":  "Epirubicin",
                                                                 "target":  "Anthracycline",
                                                                 "pathway":  "DNA replication",
                                                                 "pred_ic50":  "-0.8728906",
                                                                 "combined_score":  "12.5",
                                                                 "category":  "Candidate"
                                                             },
                                                             {
                                                                 "final_rank":  "2",
                                                                 "drug_name":  "Dinaciclib",
                                                                 "target":  "CDK1, CDK2, CDK5, CDK9",
                                                                 "pathway":  "Cell cycle",
                                                                 "pred_ic50":  "-0.2938245",
                                                                 "combined_score":  "12.0",
                                                                 "category":  "Candidate"
                                                             },
                                                             {
                                                                 "final_rank":  "3",
                                                                 "drug_name":  "Staurosporine",
                                                                 "target":  "Broad spectrum kinase inhibitor",
                                                                 "pathway":  "RTK signaling",
                                                                 "pred_ic50":  "0.10231618",
                                                                 "combined_score":  "11.5",
                                                                 "category":  "Candidate"
                                                             },
                                                             {
                                                                 "final_rank":  "4",
                                                                 "drug_name":  "Topotecan",
                                                                 "target":  "TOP1",
                                                                 "pathway":  "DNA replication",
                                                                 "pred_ic50":  "0.20960614",
                                                                 "combined_score":  "11.0",
                                                                 "category":  "Candidate"
                                                             },
                                                             {
                                                                 "final_rank":  "5",
                                                                 "drug_name":  "TW 37",
                                                                 "target":  "BCL2, BCL-XL, MCL1",
                                                                 "pathway":  "Apoptosis regulation",
                                                                 "pred_ic50":  "0.47597197",
                                                                 "combined_score":  "10.5",
                                                                 "category":  "Candidate"
                                                             }
                                                         ]
                                            },
                                  "stage_tables":  [
                                                       {
                                                           "stage":  "Stage0 Raw Cohort Split",
                                                           "input_tables":  "label, sample, drug, lincs, drug_target (raw full)",
                                                           "output_tables":  "raw_inputs/*.parquet",
                                                           "row_summary":  "label 12538 -\u003e 10598, sample 20443404 -\u003e 354552",
                                                           "feature_summary":  "cohort retention 84.53%",
                                                           "note":  "rule mode: any"
                                                       },
                                                       {
                                                           "stage":  "Stage1 FE Input Build",
                                                           "input_tables":  "raw_inputs/label + sample + drug",
                                                           "output_tables":  "fe_inputs/sample_features, drug_features, labels",
                                                           "row_summary":  "label_pair=10598, sample_rows=20, drug_rows=295",
                                                           "feature_summary":  "sample_cols=17932, drug_cols=5",
                                                           "note":  "sample join_rate=52.61%"
                                                       },
                                                       {
                                                           "stage":  "Stage2 Training Feature Matrix",
                                                           "input_tables":  "fe_inputs/sample_features + drug_features + labels",
                                                           "output_tables":  "features/features.parquet + features/labels.parquet",
                                                           "row_summary":  "features_rows=5576, labels_rows=5576",
                                                           "feature_summary":  "features_cols=17920",
                                                           "note":  "dropped_low_variance_columns=17"
                                                       },
                                                       {
                                                           "stage":  "Stage3 Pair Feature Engineering",
                                                           "input_tables":  "features + pair sources(lincs, target, chem)",
                                                           "output_tables":  "pair_features/pair_features_newfe_v2.parquet",
                                                           "row_summary":  "pairs=5576",
                                                           "feature_summary":  "lincs_metrics=5, target_cols=10",
                                                           "note":  "invalid_smiles_ratio=100%"
                                                       },
                                                       {
                                                           "stage":  "Stage4 Model Bank (ML/DL/Graph)",
                                                           "input_tables":  "features + pair_features + labels",
                                                           "output_tables":  "model_results/ml_results.json, dl_results.json, graph_results.json",
                                                           "row_summary":  "ML=0, DL=0, Graph=0",
                                                           "feature_summary":  "same model input matrix from Stage2+3",
                                                           "note":  "skip_flags: ml=start_at_post_step4, dl=start_at_post_step4, graph=start_at_post_step4"
                                                       },
                                                       {
                                                           "stage":  "Stage5 Ensemble",
                                                           "input_tables":  "Stage4 model outputs",
                                                           "output_tables":  "ensemble_results.json + top30_drugs.csv + top15_drugs.csv",
                                                           "row_summary":  "top30=30, top15=15",
                                                           "feature_summary":  "ensemble_n_models=6, spearman=0.564",
                                                           "note":  "method=spearman_weighted_average"
                                                       },
                                                       {
                                                           "stage":  "Stage6 External Validation",
                                                           "input_tables":  "top30_drugs + external cohort datasets",
                                                           "output_tables":  "top15_validated.csv + step6 results json",
                                                           "row_summary":  "validated_top15=15",
                                                           "feature_summary":  "target_expressed=29/30, P@15=0.1333",
                                                           "note":  "set=TCGA-COAD + GSE39582"
                                                       },
                                                       {
                                                           "stage":  "Stage7 ADMET Gate",
                                                           "input_tables":  "top15_validated + drug safety profiles",
                                                           "output_tables":  "final_drug_candidates.csv + step7_admet_results.json",
                                                           "row_summary":  "input=15, output=15, assays=22",
                                                           "feature_summary":  "approved=0, candidate=15",
                                                           "note":  "final score = efficacy + safety composite"
                                                       }
                                                   ]
                              },
                    "rectal":  {
                                   "cohort":  "rectal",
                                   "split_counts":  {
                                                        "label_before":  12538,
                                                        "label_after":  1380,
                                                        "sample_before":  20443404,
                                                        "sample_after":  70998,
                                                        "drug_before":  295,
                                                        "drug_after":  281,
                                                        "lincs_before":  101,
                                                        "lincs_after":  92,
                                                        "target_before":  485,
                                                        "target_after":  459
                                                    },
                                   "features":  {
                                                    "rows":  1099,
                                                    "cols":  17877
                                                },
                                   "labels":  {
                                                  "rows":  1099,
                                                  "unique_samples":  4,
                                                  "unique_drugs":  281
                                              },
                                   "pair_features":  {
                                                         "pairs":  1099,
                                                         "pair_features_newfe_rows":  1099,
                                                         "pair_features_newfe_v2_rows":  1099
                                                     },
                                   "chem_qc":  {
                                                   "drug_rows":  281,
                                                   "invalid_smiles_count":  281,
                                                   "invalid_smiles_ratio":  1.0,
                                                   "rdkit_enabled":  false,
                                                   "rdkit_error":  "rdkit_disabled_for_stability_in_current_runtime",
                                                   "chem_fallback_mode":  "all_zero_morgan_and_nan_descriptors_then_final_numeric_fillna_zero"
                                               },
                                   "pipeline":  {
                                                    "ml_ok_count":  8,
                                                    "dl_ok_count":  5,
                                                    "graph_ok_count":  2,
                                                    "ml_skipped_reason":  null,
                                                    "dl_skipped_reason":  null,
                                                    "graph_skipped_reason":  null,
                                                    "ml_results_exists":  true,
                                                    "dl_results_exists":  true,
                                                    "graph_results_exists":  true,
                                                    "ensemble_ok":  true,
                                                    "step6_ok":  true,
                                                    "step7_ok":  true,
                                                    "ensemble_error":  null,
                                                    "step6_error":  null,
                                                    "step7_error":  null,
                                                    "run_mode":  "full"
                                                },
                                   "ensemble":  {
                                                    "n_models":  6,
                                                    "spearman":  0.4609954849697509,
                                                    "rmse":  2.0950757777139279,
                                                    "pearson":  0.50473762349340068,
                                                    "r2":  0.23907996602365919,
                                                    "weights":  {
                                                                    "CatBoost":  0.23069261951843328,
                                                                    "LightGBM":  0.19961147271385851,
                                                                    "XGBoost":  0.21433855773925808,
                                                                    "FlatMLP":  0.078373025779107722,
                                                                    "ResidualMLP":  0.0967703440785656,
                                                                    "Cross-Attention":  0.18021398017077675
                                                                }
                                                },
                                   "step6":  {
                                                 "type":  "METABRIC",
                                                 "top15_count":  15,
                                                 "target_expressed":  "29/30",
                                                 "precision_at_15":  0.6,
                                                 "precision_at_20":  0.55
                                             },
                                   "step7":  {
                                                 "n_assays":  22,
                                                 "n_input":  15,
                                                 "n_output":  15,
                                                 "candidate_count":  11,
                                                 "approved_count":  4,
                                                 "top5":  [
                                                              {
                                                                  "final_rank":  "1",
                                                                  "drug_name":  "Dactinomycin",
                                                                  "target":  "RNA polymerase",
                                                                  "pathway":  "Other",
                                                                  "pred_ic50":  "0.5880703",
                                                                  "combined_score":  "14.0",
                                                                  "category":  "Approved"
                                                              },
                                                              {
                                                                  "final_rank":  "2",
                                                                  "drug_name":  "Vinblastine",
                                                                  "target":  "Microtubule destabiliser",
                                                                  "pathway":  "Mitosis",
                                                                  "pred_ic50":  "1.1874893",
                                                                  "combined_score":  "13.0",
                                                                  "category":  "Approved"
                                                              },
                                                              {
                                                                  "final_rank":  "3",
                                                                  "drug_name":  "Epirubicin",
                                                                  "target":  "Anthracycline",
                                                                  "pathway":  "DNA replication",
                                                                  "pred_ic50":  "0.35609204",
                                                                  "combined_score":  "12.5",
                                                                  "category":  "Candidate"
                                                              },
                                                              {
                                                                  "final_rank":  "4",
                                                                  "drug_name":  "Topotecan",
                                                                  "target":  "TOP1",
                                                                  "pathway":  "DNA replication",
                                                                  "pred_ic50":  "0.98041546",
                                                                  "combined_score":  "11.5",
                                                                  "category":  "Candidate"
                                                              },
                                                              {
                                                                  "final_rank":  "5",
                                                                  "drug_name":  "Paclitaxel",
                                                                  "target":  "Microtubule stabiliser",
                                                                  "pathway":  "Mitosis",
                                                                  "pred_ic50":  "1.7916642",
                                                                  "combined_score":  "11.0",
                                                                  "category":  "Approved"
                                                              }
                                                          ]
                                             },
                                   "stage_tables":  [
                                                        {
                                                            "stage":  "Stage0 Raw Cohort Split",
                                                            "input_tables":  "label, sample, drug, lincs, drug_target (raw full)",
                                                            "output_tables":  "raw_inputs/*.parquet",
                                                            "row_summary":  "label 12538 -\u003e 1380, sample 20443404 -\u003e 70998",
                                                            "feature_summary":  "cohort retention 11.01%",
                                                            "note":  "rule mode: any"
                                                        },
                                                        {
                                                            "stage":  "Stage1 FE Input Build",
                                                            "input_tables":  "raw_inputs/label + sample + drug",
                                                            "output_tables":  "fe_inputs/sample_features, drug_features, labels",
                                                            "row_summary":  "label_pair=1380, sample_rows=4, drug_rows=281",
                                                            "feature_summary":  "sample_cols=17932, drug_cols=5",
                                                            "note":  "sample join_rate=79.64%"
                                                        },
                                                        {
                                                            "stage":  "Stage2 Training Feature Matrix",
                                                            "input_tables":  "fe_inputs/sample_features + drug_features + labels",
                                                            "output_tables":  "features/features.parquet + features/labels.parquet",
                                                            "row_summary":  "features_rows=1099, labels_rows=1099",
                                                            "feature_summary":  "features_cols=17877",
                                                            "note":  "dropped_low_variance_columns=60"
                                                        },
                                                        {
                                                            "stage":  "Stage3 Pair Feature Engineering",
                                                            "input_tables":  "features + pair sources(lincs, target, chem)",
                                                            "output_tables":  "pair_features/pair_features_newfe_v2.parquet",
                                                            "row_summary":  "pairs=1099",
                                                            "feature_summary":  "lincs_metrics=5, target_cols=10",
                                                            "note":  "invalid_smiles_ratio=100%"
                                                        },
                                                        {
                                                            "stage":  "Stage4 Model Bank (ML/DL/Graph)",
                                                            "input_tables":  "features + pair_features + labels",
                                                            "output_tables":  "model_results/ml_results.json, dl_results.json, graph_results.json",
                                                            "row_summary":  "ML=8, DL=5, Graph=2",
                                                            "feature_summary":  "same model input matrix from Stage2+3",
                                                            "note":  "skip_flags: ml=, dl=, graph="
                                                        },
                                                        {
                                                            "stage":  "Stage5 Ensemble",
                                                            "input_tables":  "Stage4 model outputs",
                                                            "output_tables":  "ensemble_results.json + top30_drugs.csv + top15_drugs.csv",
                                                            "row_summary":  "top30=30, top15=15",
                                                            "feature_summary":  "ensemble_n_models=6, spearman=0.461",
                                                            "note":  "method=spearman_weighted_average"
                                                        },
                                                        {
                                                            "stage":  "Stage6 External Validation",
                                                            "input_tables":  "top30_drugs + external cohort datasets",
                                                            "output_tables":  "top15_validated.csv + step6 results json",
                                                            "row_summary":  "validated_top15=15",
                                                            "feature_summary":  "target_expressed=29/30, P@15=0.6",
                                                            "note":  "set=METABRIC"
                                                        },
                                                        {
                                                            "stage":  "Stage7 ADMET Gate",
                                                            "input_tables":  "top15_validated + drug safety profiles",
                                                            "output_tables":  "final_drug_candidates.csv + step7_admet_results.json",
                                                            "row_summary":  "input=15, output=15, assays=22",
                                                            "feature_summary":  "approved=4, candidate=11",
                                                            "note":  "final score = efficacy + safety composite"
                                                        }
                                                    ]
                               }
                }
};

