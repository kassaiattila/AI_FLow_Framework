import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AIFlow Dashboard",
  description: "AI Workflow Monitoring & Validation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="hu"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex">
        <Sidebar />
        <main className="flex-1 min-h-screen bg-muted/30">{children}</main>
      </body>
    </html>
  );
}

function Sidebar() {
  const skills = [
    { name: "invoice_processor", icon: "📄", label: "Számlák" },
    { name: "email_intent_processor", icon: "📧", label: "Email Intent" },
    { name: "aszf_rag_chat", icon: "💬", label: "RAG Chat" },
    { name: "process_documentation", icon: "📊", label: "Diagramok" },
  ];

  return (
    <aside className="w-56 border-r bg-background flex flex-col h-screen sticky top-0">
      <div className="p-4 border-b">
        <h1 className="text-lg font-bold">AIFlow</h1>
        <p className="text-xs text-muted-foreground">Workflow Dashboard</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        <a href="/" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted text-sm font-medium">
          🏠 Dashboard
        </a>
        <div className="pt-3 pb-1 px-3 text-xs font-semibold text-muted-foreground uppercase">Skills</div>
        {skills.map((s) => (
          <a key={s.name} href={`/skills/${s.name}`} className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted text-sm">
            {s.icon} {s.label}
          </a>
        ))}
        <div className="pt-3 pb-1 px-3 text-xs font-semibold text-muted-foreground uppercase">Monitoring</div>
        <a href="/costs" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted text-sm">
          💰 Költségek
        </a>
        <a href="/runs" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted text-sm">
          📋 Futások
        </a>
      </nav>
      <div className="p-3 border-t text-xs text-muted-foreground">
        v0.1.0 &middot; BestIx Kft.
      </div>
    </aside>
  );
}
