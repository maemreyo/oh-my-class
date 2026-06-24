import type { BaseQuestion, Rubric } from '../base.js'

export type SubmissionPlatform =
  | 'google_classroom'
  | 'seesaw'
  | 'microsoft_teams'
  | 'email'

// MM1: all multimedia types include submission platform info
export interface SubmissionInfo {
  platforms:   SubmissionPlatform[]
  customNote?: string
}

export interface MultimediaVideo extends BaseQuestion {
  type:               'multimedia_video'
  instructions:       string
  maxDuration:        number
  rubric?:            Rubric
  aiCheatMitigation?: string
  submission?:        SubmissionInfo
}

export interface MultimediaAudio extends BaseQuestion {
  type:        'multimedia_audio'
  instructions: string
  maxDuration: number
  rubric?:     Rubric
  submission?: SubmissionInfo
}

export interface MultimediaPhoto extends BaseQuestion {
  type:             'multimedia_photo'
  instructions:     string
  minPhotos:        number
  maxPhotos:        number
  allowAnnotations: boolean
  questions:        string[]
  submission?:      SubmissionInfo
}

export interface ExperimentDocumentation extends BaseQuestion {
  type:       'experiment_documentation'
  experiment: {
    title:     string
    materials: string[]
    steps:     string[]
  }
  documentationRequirements: {
    photos?:            { min: number }
    video?:             { maxDuration: number }
    writtenReflection?: { prompts: string[] }
  }
  submission?: SubmissionInfo
}

export interface ParentChildActivity extends BaseQuestion {
  type:         'parent_child_activity'
  title:        string
  studentTasks: Array<{ task: string; format: string }>
  parentTasks:  Array<{ task: string }>
  submission?:  SubmissionInfo
}

export interface FieldTripSection {
  name:       'pre_trip' | 'during_trip' | 'post_trip'
  prompts?:   string[]
  format?:    string
  maxEntries?: number
}

export interface FieldTripJournal extends BaseQuestion {
  type:        'field_trip_journal'
  destination: string
  sections:    FieldTripSection[]
  submission?: SubmissionInfo
}

export interface ArtProject extends BaseQuestion {
  type:          'art_project'
  prompt:        string
  documentation: {
    processPhotos?:     { min: number }
    finalPhoto?:        boolean
    writtenReflection?: { prompts: string[] }
  }
  rubric?:    Rubric
  submission?: SubmissionInfo
}

export type MultimediaQuestion =
  | MultimediaVideo
  | MultimediaAudio
  | MultimediaPhoto
  | ExperimentDocumentation
  | ParentChildActivity
  | FieldTripJournal
  | ArtProject
