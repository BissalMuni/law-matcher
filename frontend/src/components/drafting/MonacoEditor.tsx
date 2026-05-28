import Editor, { loader } from '@monaco-editor/react'
import * as monaco from 'monaco-editor'
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

// CDN을 쓰지 않고 로컬 monaco 인스턴스/워커를 사용한다 (오프라인·사내망 안전).
// 평문 조문 편집만 하므로 base editor worker 하나면 충분하다.
;(self as unknown as { MonacoEnvironment?: monaco.Environment }).MonacoEnvironment = {
  getWorker: () => new editorWorker(),
}
loader.config({ monaco })

interface Props {
  value: string
  onChange: (value: string) => void
  height?: number | string
  language?: string
  readOnly?: boolean
}

/** 입안심사 조문 편집용 Monaco 에디터 (원본 law-ebansimsa UI 충실도) */
export default function MonacoEditor({
  value,
  onChange,
  height = 360,
  language = 'markdown',
  readOnly = false,
}: Props) {
  return (
    <div style={{ border: '1px solid #d9d9d9', borderRadius: 6, overflow: 'hidden' }}>
      <Editor
        height={height}
        defaultLanguage={language}
        value={value}
        onChange={(v) => onChange(v ?? '')}
        options={{
          minimap: { enabled: false },
          wordWrap: 'on',
          lineNumbers: 'on',
          fontSize: 13,
          scrollBeyondLastLine: false,
          automaticLayout: true,
          renderWhitespace: 'none',
          readOnly,
          padding: { top: 8, bottom: 8 },
        }}
      />
    </div>
  )
}
