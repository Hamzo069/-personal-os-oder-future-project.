import { Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";

import { useAskExpenses } from "@/api/hooks";
import { Alert, Button, Card, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";

const EXAMPLES = [
  "How much did I spend on software this month?",
  "Show my spending by category this year",
  "Where did most of my money go last month?",
];

export function AskExpenses() {
  const [question, setQuestion] = useState("");
  const ask = useAskExpenses();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (question.trim().length >= 3) ask.mutate(question.trim());
  };

  return (
    <Card
      title={
        <span className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-brand-600" aria-hidden /> Ask your expenses
        </span>
      }
    >
      <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row">
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. How much did I spend on travel in August?"
          aria-label="Question about your expenses"
          maxLength={500}
        />
        <Button type="submit" loading={ask.isPending} className="sm:w-28">
          Ask
        </Button>
      </form>
      <div className="mt-2 flex flex-wrap gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => {
              setQuestion(example);
              ask.mutate(example);
            }}
            className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
          >
            {example}
          </button>
        ))}
      </div>
      {ask.isError && (
        <div className="mt-3">
          <Alert>{ask.error instanceof ApiError ? ask.error.message : "Something went wrong"}</Alert>
        </div>
      )}
      {ask.data && (
        <div className="mt-4 rounded-lg bg-slate-50 p-3">
          <pre className="whitespace-pre-wrap font-sans text-sm text-slate-800">{ask.data.answer}</pre>
          <p className="mt-2 text-xs text-slate-500">
            Interpreted as: {String(ask.data.plan.explanation ?? "")} (
            {String(ask.data.plan.intent)}
            {ask.data.plan.date_from ? `, ${String(ask.data.plan.date_from)} – ${String(ask.data.plan.date_to ?? "")}` : ""})
          </p>
        </div>
      )}
    </Card>
  );
}
