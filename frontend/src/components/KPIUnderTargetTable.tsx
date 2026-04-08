import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { KPIIndicator } from "@/data/kpiData";
import { formatTarget, getStatusColor } from "@/data/kpiData";

interface Props {
  kpis: KPIIndicator[];
}

export function KPIUnderTargetTable({ kpis }: Props) {
  const underTarget = kpis.filter((k) => k.score < 100);

  return (
    <Card className="p-5 shadow-sm border-0 shadow-foreground/5">
      <h3 className="text-sm font-semibold mb-4">KPI Under Target</h3>
      <div className="overflow-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs">KPI Indicator</TableHead>
              <TableHead className="text-xs">Target</TableHead>
              <TableHead className="text-xs">Realization</TableHead>
              <TableHead className="text-xs">Score</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {underTarget.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground text-sm py-8">
                  All KPIs are on target 🎉
                </TableCell>
              </TableRow>
            ) : (
              underTarget.map((k) => (
                <TableRow key={k.id}>
                  <TableCell className="text-sm font-medium">{k.name}</TableCell>
                  <TableCell className="text-sm">{formatTarget(k.target, k.targetUnit)}</TableCell>
                  <TableCell className="text-sm">{formatTarget(k.realization, k.targetUnit)}</TableCell>
                  <TableCell className="text-sm font-semibold">{k.score.toFixed(1)}%</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}
