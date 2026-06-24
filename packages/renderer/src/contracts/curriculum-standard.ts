export type CurriculumFramework =
  | 'moet_gdpt_2018'        // Thông tư 32/2018/TT-BGDĐT — General Education Program
  | 'moet_decision_3439'    // Quyết định 3439/QĐ-BGDĐT — AI education framework K-12
  | 'moet_circular_02_2025' // Thông tư 02/2025 — Digital Competence Framework
  | 'ccss_math'             // Common Core State Standards — Math
  | 'ccss_ela'              // Common Core State Standards — ELA
  | 'cambridge'             // Cambridge International
  | 'ielts'
  | 'custom'

export interface CurriculumStandard {
  framework:   CurriculumFramework
  code:        string   // e.g. "10-Toan-2.3.a", "CCSS.MATH.6.RP.A.1"
  description: string   // human-readable label
  grade?:      number
  subject?:    string
}
