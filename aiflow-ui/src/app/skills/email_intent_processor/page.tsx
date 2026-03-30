import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function EmailIntentProcessorPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Email Intent Processor</h2>
          <p className="text-muted-foreground">Email + csatolmany feldolgozo (hibrid ML+LLM)</p>
        </div>
        <Badge className="bg-blue-100 text-blue-800 text-sm px-3 py-1">In Development</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <FeatureCard title="Intent Classification" description="Hibrid ML (sklearn TF-IDF) + LLM (gpt-4o-mini) intent felismeres. ML <1ms, LLM fallback alacsony confidence eseten." status="Kesz" />
        <FeatureCard title="Entity Extraction" description="JSON schema vezerelt entity kinyeres: szamlaszam, ugyfelnev, datum, osszeg, stb." status="Kesz" />
        <FeatureCard title="Document Processing" description="Csatolmany feldolgozas: Docling + Azure Document Intelligence + LLM Vision multi-layer." status="Fejlesztes" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tervezett UI elemek</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>- Email preview (fejlec + body + csatolmanyok)</p>
          <p>- Intent badge (confidence szinkod) + ML vs LLM osszehasonlitas</p>
          <p>- Entity highlighting az eredeti szovegben</p>
          <p>- Routing vizualizacio (department, queue, priority)</p>
          <p>- Batch email feldolgozas + statisztikak</p>
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
