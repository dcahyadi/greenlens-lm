import { User, Bot } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { ChatMessage } from '../types'

interface Props {
  message: ChatMessage
}

export function Message({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
        isUser ? 'bg-green-600' : 'bg-slate-700'
      }`}>
        {isUser
          ? <User size={16} className="text-white" />
          : <Bot size={16} className="text-white" />
        }
      </div>
      <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
        isUser
          ? 'bg-green-600 text-white rounded-tr-sm'
          : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm'
      }`}>
        {isUser ? (
          // User messages are always plain text — no need to parse markdown
          // for content the user typed themselves.
          message.content.split('\n').map((line, i) => (
            <p key={i} className={line === '' ? 'mt-2' : ''}>{line}</p>
          ))
        ) : (
          <div className="prose-chat">
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
                ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
                li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                h1: ({ children }) => <p className="font-semibold text-slate-900 mb-1">{children}</p>,
                h2: ({ children }) => <p className="font-semibold text-slate-900 mb-1">{children}</p>,
                h3: ({ children }) => <p className="font-semibold text-slate-900 mb-1">{children}</p>,
                code: ({ children }) => (
                  <code className="bg-slate-100 text-slate-800 px-1 py-0.5 rounded text-xs">{children}</code>
                ),
                a: ({ children, href }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="text-green-700 underline">
                    {children}
                  </a>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}
