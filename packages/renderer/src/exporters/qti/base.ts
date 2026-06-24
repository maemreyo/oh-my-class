// QTI v3.0 XML helpers

export function escapeXml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

export function assessmentItem(
  identifier: string,
  title: string,
  body: string,
): string {
  return `<?xml version="1.0" encoding="UTF-8"?>
<assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v3p0"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqti_v3p0 https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_asiv3p0_v1p0.xsd"
  identifier="${escapeXml(identifier)}"
  title="${escapeXml(title)}"
  timeDependent="false">
${body}
</assessmentItem>`
}

export function responseDeclaration(
  identifier: string,
  cardinality: 'single' | 'multiple' | 'ordered',
  baseType: string,
  correctResponses: string[],
): string {
  const values = correctResponses
    .map(v => `    <value>${escapeXml(v)}</value>`)
    .join('\n')
  return `  <responseDeclaration identifier="${identifier}" cardinality="${cardinality}" baseType="${baseType}">
    <correctResponse>
${values}
    </correctResponse>
  </responseDeclaration>`
}

export function outcomeDeclaration(maxPoints: number): string {
  return `  <outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float">
    <defaultValue>
      <value>0</value>
    </defaultValue>
    <normalMaximum>${maxPoints}</normalMaximum>
  </outcomeDeclaration>`
}

export function simpleChoice(identifier: string, text: string): string {
  return `      <simpleChoice identifier="${escapeXml(identifier)}">${escapeXml(text)}</simpleChoice>`
}
