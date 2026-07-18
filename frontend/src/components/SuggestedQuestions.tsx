interface Props {
  onSelect: (q: string) => void
  language: 'en' | 'id'
}

const QUESTIONS_EN = [
  "What is Indonesia's emission reduction target in the Enhanced NDC 2022?",
  "How much financing was committed under JETP Indonesia?",
  "What carbon pricing instruments does Perpres 98/2021 introduce?",
  "What does Perpres 110/2025 change about the carbon economy?",
  "What is IDX Carbon and how does POJK 14/2023 regulate it?",
  "What is the PLTS Atap rooftop solar policy under Permen ESDM 2/2024?",
  "What are Indonesia's renewable energy targets under Perpres 112/2022?",
  "What is AMDAL and who is required to prepare one?",
  "How does PermenLHK 21/2022 implement the carbon economic value (NEK)?",
  "How does OJK's TKBI v3 2026 classify renewable energy activities?",
]

const QUESTIONS_ID = [
  "Berapa target pengurangan emisi Indonesia dalam NDC 2022?",
  "Apa itu JETP Indonesia dan berapa dana yang dijanjikan?",
  "Apa instrumen perdagangan karbon dalam Perpres 98/2021?",
  "Apa perubahan yang dibawa Perpres 110/2025 terhadap ekonomi karbon?",
  "Apa itu Bursa Karbon Indonesia (IDX Carbon) menurut POJK 14/2023?",
  "Bagaimana regulasi PLTS Atap menurut Permen ESDM 2/2024?",
  "Apa target energi terbarukan Indonesia dalam Perpres 112/2022?",
  "Apa itu AMDAL dan siapa yang wajib membuatnya?",
  "Bagaimana PermenLHK 21/2022 mengatur Nilai Ekonomi Karbon (NEK)?",
  "Bagaimana TKBI v3 2026 OJK mengklasifikasikan energi terbarukan?",
]

export function SuggestedQuestions({ onSelect, language }: Props) {
  const questions = language === 'id' ? QUESTIONS_ID : QUESTIONS_EN

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-3">
      <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-2">
        {language === 'id' ? 'Pertanyaan Populer' : 'Suggested Questions'}
      </p>
      <div className="flex flex-col gap-2">
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            className="text-left text-sm text-slate-600 bg-white border border-slate-200
                       rounded-lg px-3 py-2 hover:border-green-400 hover:text-green-700
                       hover:bg-green-50 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
