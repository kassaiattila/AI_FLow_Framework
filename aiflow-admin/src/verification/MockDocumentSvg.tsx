import {
  PAGE,
  STATIC_FIELDS,
  lineItemFields,
  resolvePath,
} from "./document-layout";

interface Props {
  invoice: Record<string, unknown>;
  width: number;
  height: number;
}

export const MockDocumentSvg = ({ invoice, width, height }: Props) => {
  const lineItems = (invoice.line_items as unknown[]) || [];
  const lineCount = Math.min(lineItems.length, 6);
  const allFields = [...STATIC_FIELDS];
  for (let i = 0; i < lineCount; i++) allFields.push(...lineItemFields(i));

  return (
    <svg
      viewBox={`0 0 ${PAGE.w} ${PAGE.h}`}
      width={width}
      height={height}
      style={{ background: "#fff" }}
    >
      {/* Page border */}
      <rect
        x={0}
        y={0}
        width={PAGE.w}
        height={PAGE.h}
        fill="white"
        stroke="#e2e8f0"
      />

      {/* Title */}
      <text
        x={PAGE.w / 2}
        y={30}
        textAnchor="middle"
        fontSize={18}
        fontWeight="bold"
        fill="#1e293b"
      >
        SZAMLA
      </text>

      {/* Vendor header */}
      <text x={35} y={85} fontSize={8} fill="#94a3b8" fontWeight="bold">
        SZALLITO
      </text>
      <line x1={35} y1={88} x2={280} y2={88} stroke="#e2e8f0" />

      {/* Buyer header */}
      <text x={335} y={85} fontSize={8} fill="#94a3b8" fontWeight="bold">
        VEVO
      </text>
      <line x1={335} y1={88} x2={560} y2={88} stroke="#e2e8f0" />

      {/* Header fields divider */}
      <line x1={35} y1={240} x2={560} y2={240} stroke="#e2e8f0" />
      <text x={35} y={246} fontSize={7} fill="#94a3b8">
        SZAMLA ADATOK
      </text>

      {/* Line items header */}
      <line x1={35} y1={290} x2={560} y2={290} stroke="#e2e8f0" />
      <text x={35} y={305} fontSize={7} fill="#94a3b8">
        #
      </text>
      <text x={65} y={305} fontSize={7} fill="#94a3b8">
        MEGNEVEZES
      </text>
      <text x={288} y={305} fontSize={7} fill="#94a3b8">
        MENNY.
      </text>
      <text x={355} y={305} fontSize={7} fill="#94a3b8">
        NETTO
      </text>
      <text x={435} y={305} fontSize={7} fill="#94a3b8">
        AFA
      </text>
      <text x={495} y={305} fontSize={7} fill="#94a3b8">
        BRUTTO
      </text>
      <line x1={35} y1={310} x2={560} y2={310} stroke="#cbd5e1" />

      {/* Line item row separators */}
      {Array.from({ length: lineCount }).map((_, i) => (
        <g key={`line-sep-${i}`}>
          <text x={42} y={335 + i * 35} fontSize={9} fill="#94a3b8">
            {i + 1}.
          </text>
          <line
            x1={35}
            y1={342 + i * 35}
            x2={560}
            y2={342 + i * 35}
            stroke="#f1f5f9"
          />
        </g>
      ))}

      {/* Totals divider */}
      <line
        x1={350}
        y1={440}
        x2={560}
        y2={440}
        stroke="#cbd5e1"
        strokeWidth={2}
      />
      <text x={355} y={455} fontSize={8} fill="#94a3b8">
        Netto:
      </text>
      <text x={355} y={480} fontSize={8} fill="#94a3b8">
        AFA:
      </text>
      <text x={355} y={512} fontSize={10} fill="#94a3b8" fontWeight="bold">
        BRUTTO:
      </text>

      {/* Render all field values */}
      {allFields.map((f) => {
        const val = resolvePath(invoice, f.fieldPath);
        return (
          <text key={f.id} x={f.x} y={f.y} fontSize={f.fontSize} fill="#1e293b">
            {val || "—"}
          </text>
        );
      })}

      {/* Footer */}
      <line x1={35} y1={800} x2={560} y2={800} stroke="#e2e8f0" />
      <text x={35} y={820} fontSize={7} fill="#94a3b8">
        {(invoice.source_file as string) || "document.pdf"} | Parser:{" "}
        {(invoice.parser_used as string) || "docling"}
      </text>
    </svg>
  );
};
