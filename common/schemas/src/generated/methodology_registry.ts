/**
 * AUTO-GENERATED from common.contracts.methodology_registry
 * DO NOT EDIT MANUALLY — run `uv run python scripts/generate_zod_schemas.py` to regenerate
 */

export const METHODOLOGY_REGISTRY = [
  {
    "tag": "concept_map",
    "labelEn": "Concept Map",
    "labelVi": "Sơ đồ khái niệm",
    "description": "Organize ideas as connected concepts for relationship-first learning.",
    "requiredComponents": [
      "vocab_cluster",
      "contrastive_pairs"
    ],
    "requirementMode": "any",
    "supportedArtifacts": [
      "lesson",
      "worksheet",
      "recap"
    ],
    "exportFormats": [
      "html",
      "h5p"
    ],
    "conflicts": [],
    "compatibleWith": [
      "contrastive_pairs",
      "active_recall"
    ]
  },
  {
    "tag": "contrastive_pairs",
    "labelEn": "Contrastive Pairs",
    "labelVi": "Cặp đối chiếu",
    "description": "Teach close concepts by comparing their boundaries and examples.",
    "requiredComponents": [
      "contrastive_pairs"
    ],
    "requirementMode": "all",
    "supportedArtifacts": [
      "lesson",
      "worksheet",
      "recap"
    ],
    "exportFormats": [
      "html",
      "h5p"
    ],
    "conflicts": [],
    "compatibleWith": [
      "concept_map",
      "why_wrong_reasoning"
    ]
  },
  {
    "tag": "film_based",
    "labelEn": "Film Based",
    "labelVi": "Học qua phim",
    "description": "Anchor learning in short clips, viewing tasks, and post-viewing synthesis.",
    "requiredComponents": [
      "film_clip_activity"
    ],
    "requirementMode": "all",
    "supportedArtifacts": [
      "lesson",
      "worksheet"
    ],
    "exportFormats": [
      "html"
    ],
    "conflicts": [],
    "compatibleWith": []
  },
  {
    "tag": "shy_student_1on1",
    "labelEn": "Shy Student 1:1",
    "labelVi": "Học 1:1 cho học sinh rụt rè",
    "description": "Use low-pressure scripts and private practice for hesitant learners.",
    "requiredComponents": [
      "roleplay_script"
    ],
    "requirementMode": "all",
    "supportedArtifacts": [
      "lesson",
      "worksheet"
    ],
    "exportFormats": [
      "html"
    ],
    "conflicts": [
      "timed_quiz"
    ],
    "compatibleWith": [
      "roleplay_script"
    ]
  },
  {
    "tag": "active_recall",
    "labelEn": "Active Recall",
    "labelVi": "Gợi nhớ chủ động",
    "description": "Prompt retrieval before explanation so students strengthen memory pathways.",
    "requiredComponents": [
      "active_recall_prompt"
    ],
    "requirementMode": "all",
    "supportedArtifacts": [
      "lesson",
      "worksheet",
      "quiz",
      "drill",
      "recap"
    ],
    "exportFormats": [
      "html",
      "gift",
      "h5p"
    ],
    "conflicts": [],
    "compatibleWith": [
      "concept_map",
      "timed_quiz",
      "inverse_thinking"
    ]
  },
  {
    "tag": "why_wrong_reasoning",
    "labelEn": "Why Wrong Reasoning",
    "labelVi": "Vì sao sai",
    "description": "Explain distractors and wrong paths so misconceptions become visible.",
    "requiredComponents": [
      "wrong_reasons"
    ],
    "requirementMode": "all",
    "supportedArtifacts": [
      "lesson",
      "worksheet",
      "quiz",
      "drill",
      "recap"
    ],
    "exportFormats": [
      "html",
      "gift",
      "h5p"
    ],
    "conflicts": [],
    "compatibleWith": [
      "contrastive_pairs"
    ]
  },
  {
    "tag": "timed_quiz",
    "labelEn": "Timed Quiz",
    "labelVi": "Bài kiểm tra tính giờ",
    "description": "Add time-boxed practice while preserving accessibility and feedback.",
    "requiredComponents": [
      "time_limit"
    ],
    "requirementMode": "all",
    "supportedArtifacts": [
      "quiz",
      "drill"
    ],
    "exportFormats": [
      "html",
      "gift",
      "h5p"
    ],
    "conflicts": [],
    "compatibleWith": [
      "active_recall"
    ]
  },
  {
    "tag": "roleplay_script",
    "labelEn": "Roleplay Script",
    "labelVi": "Kịch bản đóng vai",
    "description": "Give students structured dialogue practice with separated teacher notes.",
    "requiredComponents": [
      "roleplay_script"
    ],
    "requirementMode": "all",
    "supportedArtifacts": [
      "lesson",
      "worksheet"
    ],
    "exportFormats": [
      "html"
    ],
    "conflicts": [
      "timed_quiz"
    ],
    "compatibleWith": [
      "shy_student_1on1"
    ]
  },
  {
    "tag": "inverse_thinking",
    "labelEn": "Inverse Thinking",
    "labelVi": "Tư duy ngược",
    "description": "Start from a disaster, inspect clues, define the safe zone, and file the rule.",
    "requiredComponents": [
      "case_flow",
      "summary_table"
    ],
    "requirementMode": "all",
    "supportedArtifacts": [
      "lesson",
      "worksheet",
      "quiz",
      "recap"
    ],
    "exportFormats": [
      "html",
      "gift",
      "h5p"
    ],
    "conflicts": [],
    "compatibleWith": [
      "active_recall"
    ]
  }
] as const;

export type MethodologyRegistryEntry = (typeof METHODOLOGY_REGISTRY)[number];
export type MethodologyRegistryTag = MethodologyRegistryEntry["tag"];
