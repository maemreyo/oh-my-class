import { strToU8, zip } from 'fflate'

export type H5PContentType =
  | 'H5P.MultiChoice'
  | 'H5P.TrueFalse'
  | 'H5P.Blanks'
  | 'H5P.Flashcards'
  | 'H5P.Summary'

export interface H5PPackageOptions {
  title:       string
  mainLibrary: H5PContentType
  content:     unknown   // content.json body (validated by semantics.json in the library)
  language?:   string
}

/**
 * Build a valid .h5p ZIP file as a Uint8Array.
 * .h5p files are ZIP archives containing h5p.json + content/content.json.
 */
export async function buildH5PPackage(opts: H5PPackageOptions): Promise<Uint8Array> {
  const majorMinor = getLibraryVersion(opts.mainLibrary)
  const h5pJson = {
    title:       opts.title,
    language:    opts.language ?? 'en',
    mainLibrary: opts.mainLibrary,
    embedTypes:  ['div'],
    license:     'U',
    preloadedDependencies: [
      { machineName: opts.mainLibrary, ...majorMinor },
    ],
  }

  const contentJson = opts.content

  return new Promise((resolve, reject) => {
    zip(
      {
        'h5p.json':              strToU8(JSON.stringify(h5pJson, null, 2)),
        'content/content.json':  strToU8(JSON.stringify(contentJson, null, 2)),
      },
      (err, data) => {
        if (err) reject(err)
        else resolve(data)
      },
    )
  })
}

function getLibraryVersion(lib: H5PContentType): { majorVersion: number; minorVersion: number } {
  const versions: Record<H5PContentType, { majorVersion: number; minorVersion: number }> = {
    'H5P.MultiChoice': { majorVersion: 1, minorVersion: 16 },
    'H5P.TrueFalse':   { majorVersion: 1, minorVersion: 8 },
    'H5P.Blanks':      { majorVersion: 1, minorVersion: 14 },
    'H5P.Flashcards':  { majorVersion: 1, minorVersion: 7 },
    'H5P.Summary':     { majorVersion: 1, minorVersion: 10 },
  }
  return versions[lib]
}
