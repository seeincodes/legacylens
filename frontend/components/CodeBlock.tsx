interface CodeBlockProps {
  code: string;
  filePath: string;
  lineStart: number;
  lineEnd: number;
}

export default function CodeBlock({ code, filePath, lineStart, lineEnd }: CodeBlockProps) {
  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      <div className="px-4 py-2 bg-gray-800 text-gray-300 text-xs font-mono flex justify-between">
        <span>{filePath}</span>
        <span>Lines {lineStart}-{lineEnd}</span>
      </div>
      <pre className="p-4 text-sm text-gray-100 overflow-x-auto">
        <code>{code}</code>
      </pre>
    </div>
  );
}
