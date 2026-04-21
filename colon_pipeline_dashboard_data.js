window.COLON_DASHBOARD_DATA = {
    "run_id":  "20260418_crc_v1",
    "generated_at":  "2026-04-20 22:54:28",
    "qc":  {
               "label_pair_rows":  12538,
               "unmatched_samples":  5863,
               "unmatched_drugs":  0,
               "join_rate_samples":  0.5323815600574254,
               "join_rate_drugs":  1.0,
               "labels_unique_samples":  46,
               "labels_unique_drugs":  295,
               "sample_features_rows":  1150,
               "sample_features_cols":  18444,
               "drug_features_rows":  295,
               "missing_smiles_rows":  52,
               "missing_smiles_rate":  0.17627118644067796
           },
    "features":  {
                     "features_rows":  6675,
                     "features_cols":  18288,
                     "labels_rows":  6675,
                     "pair_rows":  6675,
                     "pair_newfe_rows":  6675,
                     "pair_newfe_v2_rows":  6675,
                     "target_missing_drug_count":  0,
                     "target_overlap_mean":  0.027565543071161047,
                     "target_overlap_max":  2.0,
                     "target_expr_mean":  0.15739824807642816
                 },
    "ensemble":  {
                     "spearman":  0.823777198704146,
                     "rmse":  1.2925302072643212,
                     "pearson":  0.8799628070971652,
                     "r2":  0.773618877519499,
                     "weights":  {
                                     "CatBoost":  0.16837326362052402,
                                     "LightGBM":  0.16692779332942703,
                                     "XGBoost":  0.167211655295667,
                                     "FlatMLP":  0.16619343545365065,
                                     "ResidualMLP":  0.16448992746363345,
                                     "Cross-Attention":  0.1668039248370979
                                 }
                 },
    "metabric":  {
                     "target_expressed":  "29/30",
                     "survival_significant":  28,
                     "p_at_15":  0.8,
                     "p_at_20":  0.75
                 },
    "models":  {
                   "ml":  [
                              {
                                  "model":  "1_LightGBM",
                                  "spearman_mean":  0.8116022066834485,
                                  "rmse_mean":  1.3429875156950946,
                                  "pearson_mean":  0.8693350725594711,
                                  "r2_mean":  0.7547821001383266
                              },
                              {
                                  "model":  "2_LightGBM_DART",
                                  "spearman_mean":  0.8078022172079662,
                                  "rmse_mean":  1.403870618157108,
                                  "pearson_mean":  0.8664067946579233,
                                  "r2_mean":  0.7322171045382546
                              },
                              {
                                  "model":  "3_XGBoost",
                                  "spearman_mean":  0.8128855666732978,
                                  "rmse_mean":  1.3353346450052865,
                                  "pearson_mean":  0.8707445400321469,
                                  "r2_mean":  0.7574863965994443
                              },
                              {
                                  "model":  "4_CatBoost",
                                  "spearman_mean":  0.8034397663656406,
                                  "rmse_mean":  1.3813883228774568,
                                  "pearson_mean":  0.863385389809223,
                                  "r2_mean":  0.740656515746295
                              },
                              {
                                  "model":  "5_RandomForest",
                                  "spearman_mean":  0.6519086748616194,
                                  "rmse_mean":  2.005307857280543,
                                  "pearson_mean":  0.7187645716534924,
                                  "r2_mean":  0.45507631029499385
                              },
                              {
                                  "model":  "6_ExtraTrees",
                                  "spearman_mean":  0.6890745535313931,
                                  "rmse_mean":  1.8645113818409302,
                                  "pearson_mean":  0.7600098451626772,
                                  "r2_mean":  0.5288867032909518
                              },
                              {
                                  "model":  "7_Stacking_Ridge",
                                  "spearman_mean":  0.693710883207125,
                                  "rmse_mean":  1.7568364985833955,
                                  "pearson_mean":  0.7694717170379053,
                                  "r2_mean":  0.5813479499065659
                              },
                              {
                                  "model":  "8_RSF",
                                  "spearman_mean":  0.6295016791162678,
                                  "rmse_mean":  599.2001778396256,
                                  "pearson_mean":  0.6665502526799185,
                                  "r2_mean":  -48713.76633701463
                              }
                          ],
                   "dl":  [
                              {
                                  "model":  "10_FlatMLP",
                                  "spearman_mean":  0.8048247870780401,
                                  "rmse_mean":  1.3773011103882844,
                                  "pearson_mean":  0.8621320724487305,
                                  "r2_mean":  0.742463207244873
                              },
                              {
                                  "model":  "11_TabNet",
                                  "spearman_mean":  0.8032678426887836,
                                  "rmse_mean":  1.3705306870703715,
                                  "pearson_mean":  0.8645526766777039,
                                  "r2_mean":  0.7449530124664306
                              },
                              {
                                  "model":  "12_FT_Transformer",
                                  "spearman_mean":  0.7886902537921545,
                                  "rmse_mean":  1.4385218460630764,
                                  "pearson_mean":  0.8497985005378723,
                                  "r2_mean":  0.7188378214836121
                              },
                              {
                                  "model":  "13_Cross_Attention",
                                  "spearman_mean":  0.7852273210438111,
                                  "rmse_mean":  1.3715888535154581,
                                  "pearson_mean":  0.8525455594062805,
                                  "r2_mean":  0.7263022065162659
                              },
                              {
                                  "model":  "9_ResidualMLP",
                                  "spearman_mean":  0.8037638797396086,
                                  "rmse_mean":  1.3783324912174266,
                                  "pearson_mean":  0.8620527982711792,
                                  "r2_mean":  0.7420430183410645
                              }
                          ],
                   "graph":  [
                                 {
                                     "model":  "14_GraphSAGE",
                                     "spearman_mean":  0.41180492597230334,
                                     "rmse_mean":  2.4142019437770297,
                                     "p_at_20_mean":  0.9099999999999999,
                                     "auroc_mean":  0.7101426708631317
                                 },
                                 {
                                     "model":  "15_GAT",
                                     "spearman_mean":  0.03957611623565288,
                                     "rmse_mean":  2.703653774082164,
                                     "p_at_20_mean":  0.6300000000000001,
                                     "auroc_mean":  0.5246231726430016
                                 }
                             ]
               },
    "step6":  [
                  {
                      "final_rank":  1,
                      "drug_name":  "Bortezomib",
                      "target":  "Proteasome",
                      "pathway":  "Protein stability and degradation",
                      "mean_pred_ic50":  -4.119006,
                      "sensitivity_rate":  1.0,
                      "validation_score":  9.4
                  },
                  {
                      "final_rank":  2,
                      "drug_name":  "Dactinomycin",
                      "target":  "RNA polymerase",
                      "pathway":  "Other",
                      "mean_pred_ic50":  -3.6088626,
                      "sensitivity_rate":  1.0,
                      "validation_score":  7.85
                  },
                  {
                      "final_rank":  3,
                      "drug_name":  "Vinorelbine",
                      "target":  "Microtubule destabiliser",
                      "pathway":  "Mitosis",
                      "mean_pred_ic50":  -2.842772,
                      "sensitivity_rate":  1.0,
                      "validation_score":  9.25
                  },
                  {
                      "final_rank":  4,
                      "drug_name":  "Dactinomycin",
                      "target":  "RNA polymerase",
                      "pathway":  "Other",
                      "mean_pred_ic50":  -2.8280318,
                      "sensitivity_rate":  1.0,
                      "validation_score":  7.7
                  },
                  {
                      "final_rank":  5,
                      "drug_name":  "Docetaxel",
                      "target":  "Microtubule stabiliser",
                      "pathway":  "Mitosis",
                      "mean_pred_ic50":  -2.6400893,
                      "sensitivity_rate":  1.0,
                      "validation_score":  9.1
                  },
                  {
                      "final_rank":  6,
                      "drug_name":  "Vinblastine",
                      "target":  "Microtubule destabiliser",
                      "pathway":  "Mitosis",
                      "mean_pred_ic50":  -2.6262245,
                      "sensitivity_rate":  0.9565217391304348,
                      "validation_score":  9.05
                  },
                  {
                      "final_rank":  7,
                      "drug_name":  "Docetaxel",
                      "target":  "Microtubule stabiliser",
                      "pathway":  "Mitosis",
                      "mean_pred_ic50":  -2.5583827,
                      "sensitivity_rate":  0.9583333333333334,
                      "validation_score":  9.0
                  },
                  {
                      "final_rank":  8,
                      "drug_name":  "Paclitaxel",
                      "target":  "Microtubule stabiliser",
                      "pathway":  "Mitosis",
                      "mean_pred_ic50":  -2.2690415,
                      "sensitivity_rate":  1.0,
                      "validation_score":  8.95
                  },
                  {
                      "final_rank":  9,
                      "drug_name":  "Staurosporine",
                      "target":  "Broad spectrum kinase inhibitor",
                      "pathway":  "RTK signaling",
                      "mean_pred_ic50":  -2.1913526,
                      "sensitivity_rate":  1.0,
                      "validation_score":  7.4
                  },
                  {
                      "final_rank":  10,
                      "drug_name":  "SN-38",
                      "target":  "TOP1",
                      "pathway":  "DNA replication",
                      "mean_pred_ic50":  -2.090089,
                      "sensitivity_rate":  1.0,
                      "validation_score":  8.85
                  },
                  {
                      "final_rank":  11,
                      "drug_name":  "Dinaciclib",
                      "target":  "CDK1, CDK2, CDK5, CDK9",
                      "pathway":  "Cell cycle",
                      "mean_pred_ic50":  -2.0021646,
                      "sensitivity_rate":  1.0,
                      "validation_score":  8.8
                  },
                  {
                      "final_rank":  12,
                      "drug_name":  "Rapamycin",
                      "target":  "MTORC1",
                      "pathway":  "PI3K/MTOR signaling",
                      "mean_pred_ic50":  -1.0858057,
                      "sensitivity_rate":  1.0,
                      "validation_score":  8.7
                  },
                  {
                      "final_rank":  13,
                      "drug_name":  "Camptothecin",
                      "target":  "TOP1",
                      "pathway":  "DNA replication",
                      "mean_pred_ic50":  -1.0436155,
                      "sensitivity_rate":  0.9583333333333334,
                      "validation_score":  8.65
                  },
                  {
                      "final_rank":  14,
                      "drug_name":  "Luminespib",
                      "target":  "HSP90",
                      "pathway":  "Protein stability and degradation",
                      "mean_pred_ic50":  -0.9708665,
                      "sensitivity_rate":  0.9583333333333334,
                      "validation_score":  8.55
                  },
                  {
                      "final_rank":  15,
                      "drug_name":  "Epirubicin",
                      "target":  "Anthracycline",
                      "pathway":  "DNA replication",
                      "mean_pred_ic50":  -0.06464248,
                      "sensitivity_rate":  0.9583333333333334,
                      "validation_score":  8.25
                  }
              ],
    "step7":  [
                  {
                      "final_rank":  1,
                      "drug_name":  "Vinorelbine",
                      "target":  "Microtubule destabiliser",
                      "pathway":  "Mitosis",
                      "pred_ic50":  -2.842772,
                      "safety_score":  8.0,
                      "combined_score":  14.5,
                      "category":  "Approved",
                      "flags":  [

                                ]
                  },
                  {
                      "final_rank":  2,
                      "drug_name":  "Dactinomycin",
                      "target":  "RNA polymerase",
                      "pathway":  "Other",
                      "pred_ic50":  -3.6088626,
                      "safety_score":  7.0,
                      "combined_score":  14.0,
                      "category":  "Approved",
                      "flags":  [
                                    "DILI (Drug-Induced Liver Injury)(+)"
                                ]
                  },
                  {
                      "final_rank":  3,
                      "drug_name":  "Staurosporine",
                      "target":  "Broad spectrum kinase inhibitor",
                      "pathway":  "RTK signaling",
                      "pred_ic50":  -2.1913526,
                      "safety_score":  10.0,
                      "combined_score":  13.5,
                      "category":  "Candidate",
                      "flags":  [

                                ]
                  },
                  {
                      "final_rank":  4,
                      "drug_name":  "Dactinomycin",
                      "target":  "RNA polymerase",
                      "pathway":  "Other",
                      "pred_ic50":  -2.8280318,
                      "safety_score":  7.0,
                      "combined_score":  13.0,
                      "category":  "Approved",
                      "flags":  [
                                    "DILI (Drug-Induced Liver Injury)(+)"
                                ]
                  },
                  {
                      "final_rank":  5,
                      "drug_name":  "SN-38",
                      "target":  "TOP1",
                      "pathway":  "DNA replication",
                      "pred_ic50":  -2.090089,
                      "safety_score":  10.0,
                      "combined_score":  13.0,
                      "category":  "Candidate",
                      "flags":  [

                                ]
                  },
                  {
                      "final_rank":  6,
                      "drug_name":  "Vinblastine",
                      "target":  "Microtubule destabiliser",
                      "pathway":  "Mitosis",
                      "pred_ic50":  -2.6262245,
                      "safety_score":  7.83,
                      "combined_score":  12.83,
                      "category":  "Approved",
                      "flags":  [

                                ]
                  },
                  {
                      "final_rank":  7,
                      "drug_name":  "Bortezomib",
                      "target":  "Proteasome",
                      "pathway":  "Protein stability and degradation",
                      "pred_ic50":  -4.119006,
                      "safety_score":  5.29,
                      "combined_score":  12.79,
                      "category":  "Approved",
                      "flags":  [
                                    "DILI (Drug-Induced Liver Injury)(+)"
                                ]
                  },
                  {
                      "final_rank":  8,
                      "drug_name":  "Dinaciclib",
                      "target":  "CDK1, CDK2, CDK5, CDK9",
                      "pathway":  "Cell cycle",
                      "pred_ic50":  -2.0021646,
                      "safety_score":  10.0,
                      "combined_score":  12.5,
                      "category":  "Candidate",
                      "flags":  [

                                ]
                  },
                  {
                      "final_rank":  9,
                      "drug_name":  "Docetaxel",
                      "target":  "Microtubule stabiliser",
                      "pathway":  "Mitosis",
                      "pred_ic50":  -2.6400893,
                      "safety_score":  6.83,
                      "combined_score":  12.33,
                      "category":  "Approved",
                      "flags":  [
                                    "DILI (Drug-Induced Liver Injury)(+)"
                                ]
                  },
                  {
                      "final_rank":  10,
                      "drug_name":  "Camptothecin",
                      "target":  "TOP1",
                      "pathway":  "DNA replication",
                      "pred_ic50":  -1.0436155,
                      "safety_score":  10.0,
                      "combined_score":  11.5,
                      "category":  "Candidate",
                      "flags":  [

                                ]
                  },
                  {
                      "final_rank":  11,
                      "drug_name":  "Docetaxel",
                      "target":  "Microtubule stabiliser",
                      "pathway":  "Mitosis",
                      "pred_ic50":  -2.5583827,
                      "safety_score":  6.83,
                      "combined_score":  11.33,
                      "category":  "Approved",
                      "flags":  [
                                    "DILI (Drug-Induced Liver Injury)(+)"
                                ]
                  },
                  {
                      "final_rank":  12,
                      "drug_name":  "Paclitaxel",
                      "target":  "Microtubule stabiliser",
                      "pathway":  "Mitosis",
                      "pred_ic50":  -2.2690415,
                      "safety_score":  6.83,
                      "combined_score":  10.83,
                      "category":  "Approved",
                      "flags":  [
                                    "DILI (Drug-Induced Liver Injury)(+)"
                                ]
                  },
                  {
                      "final_rank":  13,
                      "drug_name":  "Rapamycin",
                      "target":  "MTORC1",
                      "pathway":  "PI3K/MTOR signaling",
                      "pred_ic50":  -1.0858057,
                      "safety_score":  7.71,
                      "combined_score":  9.71,
                      "category":  "Approved",
                      "flags":  [

                                ]
                  },
                  {
                      "final_rank":  14,
                      "drug_name":  "Luminespib",
                      "target":  "HSP90",
                      "pathway":  "Protein stability and degradation",
                      "pred_ic50":  -0.9708665,
                      "safety_score":  5.0,
                      "combined_score":  6.0,
                      "category":  "Candidate",
                      "flags":  [

                                ]
                  },
                  {
                      "final_rank":  15,
                      "drug_name":  "Epirubicin",
                      "target":  "Anthracycline",
                      "pathway":  "DNA replication",
                      "pred_ic50":  -0.06464248,
                      "safety_score":  2.83,
                      "combined_score":  3.33,
                      "category":  "Caution",
                      "flags":  [
                                    "Ames Mutagenicity(+)",
                                    "DILI (Drug-Induced Liver Injury)(+)"
                                ]
                  }
              ],
    "top30":  [
                  {
                      "final_rank":  1,
                      "drug_id":  "1817",
                      "drug_name":  "Romidepsin",
                      "target":  "HDAC1, HDAC2, HDAC3, HDAC8",
                      "pathway":  "Chromatin histone acetylation",
                      "mean_pred_ic50":  -4.418053150177002,
                      "mean_true_ic50":  -4.670007228851318,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  2,
                      "drug_id":  "1191",
                      "drug_name":  "Bortezomib",
                      "target":  "Proteasome",
                      "pathway":  "Protein stability and degradation",
                      "mean_pred_ic50":  -4.119006156921387,
                      "mean_true_ic50":  -4.46719217300415,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  3,
                      "drug_id":  "1911",
                      "drug_name":  "Dactinomycin",
                      "target":  "RNA polymerase",
                      "pathway":  "Other",
                      "mean_pred_ic50":  -3.6088626384735107,
                      "mean_true_ic50":  -4.243010997772217,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  4,
                      "drug_id":  "1248",
                      "drug_name":  "Daporinad",
                      "target":  "NAMPT",
                      "pathway":  "Metabolism",
                      "mean_pred_ic50":  -3.201629877090454,
                      "mean_true_ic50":  -4.055396556854248,
                      "sensitivity_rate":  1.0,
                      "n_samples":  12,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  5,
                      "drug_id":  "2048",
                      "drug_name":  "Vinorelbine",
                      "target":  "Microtubule destabiliser",
                      "pathway":  "Mitosis",
                      "mean_pred_ic50":  -2.8427720069885254,
                      "mean_true_ic50":  -2.8246216773986816,
                      "sensitivity_rate":  1.0,
                      "n_samples":  23,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  6,
                      "drug_id":  "1811",
                      "drug_name":  "Dactinomycin",
                      "target":  "RNA polymerase",
                      "pathway":  "Other",
                      "mean_pred_ic50":  -2.8280317783355713,
                      "mean_true_ic50":  -2.1989662647247314,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  7,
                      "drug_id":  "1941",
                      "drug_name":  "Sepantronium bromide",
                      "target":  "BIRC5",
                      "pathway":  "Apoptosis regulation",
                      "mean_pred_ic50":  -2.7634894847869873,
                      "mean_true_ic50":  -2.8552846908569336,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  8,
                      "drug_id":  "1007",
                      "drug_name":  "Docetaxel",
                      "target":  "Microtubule stabiliser",
                      "pathway":  "Mitosis",
                      "mean_pred_ic50":  -2.640089273452759,
                      "mean_true_ic50":  -3.666675567626953,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  9,
                      "drug_id":  "1004",
                      "drug_name":  "Vinblastine",
                      "target":  "Microtubule destabiliser",
                      "pathway":  "Mitosis",
                      "mean_pred_ic50":  -2.6262245178222656,
                      "mean_true_ic50":  -2.710850477218628,
                      "sensitivity_rate":  0.9565217391304348,
                      "n_samples":  23,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  10,
                      "drug_id":  "1819",
                      "drug_name":  "Docetaxel",
                      "target":  "Microtubule stabiliser",
                      "pathway":  "Mitosis",
                      "mean_pred_ic50":  -2.558382749557495,
                      "mean_true_ic50":  -1.588708758354187,
                      "sensitivity_rate":  0.9583333333333334,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  11,
                      "drug_id":  "1080",
                      "drug_name":  "Paclitaxel",
                      "target":  "Microtubule stabiliser",
                      "pathway":  "Mitosis",
                      "mean_pred_ic50":  -2.2690415382385254,
                      "mean_true_ic50":  -2.1340115070343018,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  12,
                      "drug_id":  "1034",
                      "drug_name":  "Staurosporine",
                      "target":  "Broad spectrum kinase inhibitor",
                      "pathway":  "RTK signaling",
                      "mean_pred_ic50":  -2.191352605819702,
                      "mean_true_ic50":  -2.397461175918579,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  13,
                      "drug_id":  "1494",
                      "drug_name":  "SN-38",
                      "target":  "TOP1",
                      "pathway":  "DNA replication",
                      "mean_pred_ic50":  -2.0900890827178955,
                      "mean_true_ic50":  -2.6705386638641357,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  14,
                      "drug_id":  "1180",
                      "drug_name":  "Dinaciclib",
                      "target":  "CDK1, CDK2, CDK5, CDK9",
                      "pathway":  "Cell cycle",
                      "mean_pred_ic50":  -2.002164602279663,
                      "mean_true_ic50":  -2.2013628482818604,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  15,
                      "drug_id":  "1372",
                      "drug_name":  "Trametinib",
                      "target":  "MEK1, MEK2",
                      "pathway":  "ERK MAPK signaling",
                      "mean_pred_ic50":  -1.9045077562332153,
                      "mean_true_ic50":  -2.2669219970703125,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  16,
                      "drug_id":  "1084",
                      "drug_name":  "Rapamycin",
                      "target":  "MTORC1",
                      "pathway":  "PI3K/MTOR signaling",
                      "mean_pred_ic50":  -1.0858056545257568,
                      "mean_true_ic50":  -1.3654894828796387,
                      "sensitivity_rate":  1.0,
                      "n_samples":  22,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  17,
                      "drug_id":  "1003",
                      "drug_name":  "Camptothecin",
                      "target":  "TOP1",
                      "pathway":  "DNA replication",
                      "mean_pred_ic50":  -1.043615460395813,
                      "mean_true_ic50":  -1.3878345489501953,
                      "sensitivity_rate":  0.9583333333333334,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  18,
                      "drug_id":  "1862",
                      "drug_name":  "MG-132",
                      "target":  "Proteasome, CAPN1",
                      "pathway":  "Protein stability and degradation",
                      "mean_pred_ic50":  -1.0240191221237183,
                      "mean_true_ic50":  -1.2517876625061035,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  19,
                      "drug_id":  "1559",
                      "drug_name":  "Luminespib",
                      "target":  "HSP90",
                      "pathway":  "Protein stability and degradation",
                      "mean_pred_ic50":  -0.9708665013313293,
                      "mean_true_ic50":  -1.150758147239685,
                      "sensitivity_rate":  0.9583333333333334,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  20,
                      "drug_id":  "1060",
                      "drug_name":  "PD0325901",
                      "target":  "MEK1, MEK2",
                      "pathway":  "ERK MAPK signaling",
                      "mean_pred_ic50":  -0.6145191788673401,
                      "mean_true_ic50":  -0.8304508328437805,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  21,
                      "drug_id":  "1086",
                      "drug_name":  "BI-2536",
                      "target":  "PLK1, PLK2, PLK3",
                      "pathway":  "Cell cycle",
                      "mean_pred_ic50":  -0.5589472055435181,
                      "mean_true_ic50":  -0.6629890203475952,
                      "sensitivity_rate":  0.9130434782608695,
                      "n_samples":  23,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  22,
                      "drug_id":  "1057",
                      "drug_name":  "Dactolisib",
                      "target":  "PI3K (class 1), MTORC1, MTORC2",
                      "pathway":  "PI3K/MTOR signaling",
                      "mean_pred_ic50":  -0.47223544120788574,
                      "mean_true_ic50":  -0.6220092177391052,
                      "sensitivity_rate":  0.9583333333333334,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  23,
                      "drug_id":  "1026",
                      "drug_name":  "Tanespimycin",
                      "target":  "HSP90",
                      "pathway":  "Protein stability and degradation",
                      "mean_pred_ic50":  -0.4145629107952118,
                      "mean_true_ic50":  -0.5264946818351746,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  24,
                      "drug_id":  "1008",
                      "drug_name":  "Methotrexate",
                      "target":  "Antimetabolite",
                      "pathway":  "DNA replication",
                      "mean_pred_ic50":  -0.1021634116768837,
                      "mean_true_ic50":  -0.13722652196884155,
                      "sensitivity_rate":  0.9583333333333334,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  25,
                      "drug_id":  "1511",
                      "drug_name":  "Epirubicin",
                      "target":  "Anthracycline",
                      "pathway":  "DNA replication",
                      "mean_pred_ic50":  -0.06464248150587082,
                      "mean_true_ic50":  -0.0372922457754612,
                      "sensitivity_rate":  0.9583333333333334,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  26,
                      "drug_id":  "1024",
                      "drug_name":  "Lestaurtinib",
                      "target":  "FLT3, JAK2, NTRK1, NTRK2, NTRK3",
                      "pathway":  "Other kinases",
                      "mean_pred_ic50":  -0.019029809162020683,
                      "mean_true_ic50":  0.0937839150428772,
                      "sensitivity_rate":  0.9583333333333334,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  27,
                      "drug_id":  "1825",
                      "drug_name":  "Podophyllotoxin bromide",
                      "target":  "\u003cNA\u003e",
                      "pathway":  "Unclassified",
                      "mean_pred_ic50":  0.1626637578010559,
                      "mean_true_ic50":  -0.0016641641268506646,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  28,
                      "drug_id":  "1849",
                      "drug_name":  "Sabutoclax",
                      "target":  "BCL2, BCL-XL, BFL1, MCL1",
                      "pathway":  "Apoptosis regulation",
                      "mean_pred_ic50":  0.2715638279914856,
                      "mean_true_ic50":  0.105368971824646,
                      "sensitivity_rate":  1.0,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  29,
                      "drug_id":  "1022",
                      "drug_name":  "AZD7762",
                      "target":  "CHEK1, CHEK2",
                      "pathway":  "Cell cycle",
                      "mean_pred_ic50":  0.3274199962615967,
                      "mean_true_ic50":  0.058428507298231125,
                      "sensitivity_rate":  0.9583333333333334,
                      "n_samples":  24,
                      "category":  "Validated"
                  },
                  {
                      "final_rank":  30,
                      "drug_id":  "1190",
                      "drug_name":  "Gemcitabine",
                      "target":  "Pyrimidine antimetabolite",
                      "pathway":  "DNA replication",
                      "mean_pred_ic50":  0.35100409388542175,
                      "mean_true_ic50":  0.13930052518844604,
                      "sensitivity_rate":  0.8333333333333334,
                      "n_samples":  24,
                      "category":  "Validated"
                  }
              ]
};

