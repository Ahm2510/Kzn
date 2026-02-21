import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface DataTableProps {
  columns: string[];
  rows: (string | number)[][];
  maxRows?: number;
  className?: string;
}

export function DataTable({ 
  columns, 
  rows, 
  maxRows = 5,
  className 
}: DataTableProps) {
  const displayRows = rows.slice(0, maxRows);
  const hasMore = rows.length > maxRows;

  return (
    <div className={cn("rounded-lg border border-border overflow-hidden", className)}>
      <Table>
        <TableHeader>
          <TableRow className="bg-card hover:bg-card">
            {columns.map((col, i) => (
              <TableHead 
                key={i} 
                className="text-xs font-mono font-medium text-muted-foreground h-10"
              >
                {col}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayRows.map((row, rowIndex) => (
            <TableRow key={rowIndex} className="hover:bg-muted/30">
              {row.map((cell, cellIndex) => (
                <TableCell 
                  key={cellIndex} 
                  className="text-sm font-mono py-3"
                >
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {hasMore && (
        <div className="px-4 py-2 bg-card border-t border-border">
          <p className="text-xs text-muted-foreground">
            Showing {maxRows} of {rows.length} rows
          </p>
        </div>
      )}
    </div>
  );
}
