import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function ProcessDocumentationPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Process Documentation</h2>
          <p className="text-muted-foreground">Natural language -&gt; BPMN diagramok (Mermaid + DrawIO + SVG)</p>
        </div>
        <Badge className="bg-green-100 text-green-800 text-sm px-3 py-1">Production</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <FeatureCard title="Process Analysis" description="LLM-alapu folyamat elemzes: lane-ek, activity-k, gateway-ek, subprocess-ek azonositasa." status="Kesz" />
        <FeatureCard title="BPMN Generation" description="Strukturalt XML BPMN swimlane diagram generalas. Mermaid + DrawIO + SVG output." status="Kesz" />
        <FeatureCard title="Diagram Render" description="Kroki szerveren keresztul SVG rendereles. Mermaid flowchart + DrawIO preview." status="Kesz" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tervezett UI elemek</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>- Szoveg input (folyamat leiras termeszetes nyelven)</p>
          <p>- Mermaid diagram rendereles (iframe Kroki-val)</p>
          <p>- DrawIO preview es letoltes</p>
          <p>- Step trace: classify, elaborate, extract, review, generate</p>
          <p>- Korabbi generalt diagramok galeria</p>
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
