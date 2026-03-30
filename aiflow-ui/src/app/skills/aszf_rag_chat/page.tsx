import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function AszfRagChatPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">ASZF RAG Chat</h2>
          <p className="text-muted-foreground">Jogi dokumentum RAG chat (docling + pgvector + OpenAI)</p>
        </div>
        <Badge className="bg-green-100 text-green-800 text-sm px-3 py-1">85% eval pass</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <FeatureCard title="Hybrid Search" description="pgvector HNSW + BM25 tsvector + RRF fusion. 7 chunk atlagos relevancia." status="Kesz" />
        <FeatureCard title="Hallucination Check" description="Automatikus hallucination score (threshold: 0.15). 86% pass rate az eval-on." status="Kesz" />
        <FeatureCard title="Citation Panel" description="Valas-alapu citation megjelentes a forras chunk-okbol." status="Fejlesztes" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tervezett UI elemek</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>- Chat interface (kerdes-valasz + citation panel)</p>
          <p>- Hallucination score vizualis jelzo (zold/sarga/piros)</p>
          <p>- Search results relevancia score sav</p>
          <p>- Step-by-step trace: rewrite, search, context, answer, cite, hallucination</p>
          <p>- Chunk highlight: melyik chunk-bol jott a valasz</p>
        </CardContent>
      </Card>
    </div>
  );
}

function FeatureCard({ title, description, status }: { title: string; description: string; status: string }) {
  const color = status === "Kesz" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800";
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-medium">{title}</p>
          <Badge className={`${color} text-[10px]`}>{status}</Badge>
        </div>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}
