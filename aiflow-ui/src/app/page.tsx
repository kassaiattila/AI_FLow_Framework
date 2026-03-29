import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SKILLS } from "@/lib/types";

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <p className="text-muted-foreground">AIFlow Workflow Monitoring</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard title="Skills" value="6" subtitle="4 aktiv, 1 stub" />
        <KpiCard title="Tesztek" value="157" subtitle="869 PASS" />
        <KpiCard title="Mai futasok" value="20" subtitle="szamla feldolgozas" />
        <KpiCard title="Mai koltseg" value="$0.14" subtitle="gpt-4o extraction" />
      </div>

      {/* Skill Grid */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Skill-ek</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SKILLS.map((skill) => (
            <a key={skill.name} href={`/skills/${skill.name}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">{skill.display_name}</CardTitle>
                    <StatusBadge status={skill.status} />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground mb-2">{skill.description}</p>
                  <p className="text-xs text-muted-foreground">{skill.test_count} teszt</p>
                </CardContent>
              </Card>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

function KpiCard({ title, value, subtitle }: { title: string; value: string; subtitle: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className="text-3xl font-bold mt-1">{value}</p>
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "production") return <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Production</Badge>;
  if (status === "stub") return <Badge variant="outline" className="text-gray-500">Stub</Badge>;
  return <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">{status}</Badge>;
}
