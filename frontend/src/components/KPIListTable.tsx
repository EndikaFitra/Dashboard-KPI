import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { KPIIndicator } from "@/data/kpiData";
import { formatTarget } from "@/data/kpiData";

interface Props {
  kpis: KPIIndicator[];
}

export function KPIListTable({ kpis }: Props) {
  return (
    <Card className="p-4 md:p-5 shadow-sm border-0 shadow-foreground/5">
      <h3 className="text-sm font-semibold mb-4">KPI List</h3>
      {/* Negative horizontal margin + px padding creates horizontal scroll on mobile
          without clipping rounded card corners */}
      <div className="overflow-x-auto -mx-4 md:mx-0 px-4 md:px-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs min-w-[160px]">KPI Indicator</TableHead>
              <TableHead className="text-xs text-right whitespace-nowrap">Target</TableHead>
              <TableHead className="text-xs text-right whitespace-nowrap">Realization</TableHead>
              <TableHead className="text-xs text-right whitespace-nowrap">Achievement</TableHead>
              <TableHead className="text-xs text-center whitespace-nowrap hidden sm:table-cell">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {kpis.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground text-sm py-8">
                  No KPI data available.
                </TableCell>
              </TableRow>
            ) : (
              kpis.map((k) => {
                const onTarget = k.score >= 100;
                return (
                  <TableRow key={k.id}>
                    <TableCell className="text-sm font-medium">{k.name}</TableCell>
                    <TableCell className="text-sm text-right">{formatTarget(k.target, k.targetUnit)}</TableCell>
                    <TableCell className="text-sm text-right">{formatTarget(k.realization, k.targetUnit)}</TableCell>
                    <TableCell className="text-sm text-right">
                      <span className={`font-semibold tabular-nums ${onTarget ? "text-emerald-600" : "text-blue-600"}`}>
                        {Number(k.score).toFixed(2)}%
                      </span>
                    </TableCell>
                    <TableCell className="text-center hidden sm:table-cell">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-medium ${
                        onTarget ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700"
                      }`}>
                        {onTarget ? "On Target" : "On Progress"}
                      </span>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}
