import { useState } from "react"
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getExpandedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
  type ExpandedState,
} from "@tanstack/react-table"
import {
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  ChevronRight,
  Download,
  Box,
  CheckCircle,
  XCircle,
} from "lucide-react"
import { cn, fmt, scoreColor, dockingColor } from "../lib/utils"
import type { MoleculeResult, ScreeningResults } from "../api/client"
import { MolCard } from "./MolCard"

const colHelper = createColumnHelper<MoleculeResult>()

interface ResultsTableProps {
  data: ScreeningResults
  jobId: string
  onViewPose: (mol: MoleculeResult) => void
  onPageChange: (page: number) => void
  exportCsvUrl: string
}

export function ResultsTable({
  data,
  onViewPose,
  onPageChange,
  exportCsvUrl,
}: ResultsTableProps) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [expanded, setExpanded] = useState<ExpandedState>({})

  const columns = [
    colHelper.accessor("rank", {
      header: "#",
      cell: (info) => (
        <span className="font-mono text-slate-400 text-xs">
          {info.getValue()}
        </span>
      ),
      size: 48,
    }),
    colHelper.accessor("name", {
      header: "Name",
      cell: (info) => (
        <span className="font-semibold text-slate-200 text-xs truncate block max-w-[140px]">
          {info.getValue()}
        </span>
      ),
    }),
    colHelper.accessor("ensemble_score", {
      header: "Ensemble",
      cell: (info) => (
        <span
          className={cn(
            "font-mono text-xs font-bold",
            scoreColor(info.getValue()),
          )}
        >
          {fmt(info.getValue(), 3)}
        </span>
      ),
    }),
    colHelper.accessor("predicted_pic50", {
      header: "pIC50",
      cell: (info) => {
        const row = info.row.original
        return (
          <div className="text-xs">
            <span
              className={cn("font-mono font-bold", scoreColor(info.getValue()))}
            >
              {fmt(info.getValue(), 2)}
            </span>
            {row.pic50_uncertainty != null && (
              <span className="text-slate-600 ml-1">
                ±{fmt(row.pic50_uncertainty, 2)}
              </span>
            )}
          </div>
        )
      },
    }),
    colHelper.accessor("docking_score", {
      header: "Docking",
      cell: (info) => (
        <span
          className={cn(
            "font-mono text-xs font-bold",
            dockingColor(info.getValue()),
          )}
        >
          {info.getValue() != null ? `${fmt(info.getValue(), 2)}` : "—"}
        </span>
      ),
    }),
    colHelper.display({
      id: "lipinski_mw",
      header: "MW",
      cell: ({ row }) => (
        <span className="text-xs text-slate-400 font-mono">
          {fmt(row.original.lipinski?.mw, 0)}
        </span>
      ),
    }),
    colHelper.display({
      id: "lipinski_logp",
      header: "LogP",
      cell: ({ row }) => (
        <span className="text-xs text-slate-400 font-mono">
          {fmt(row.original.lipinski?.logp, 2)}
        </span>
      ),
    }),
    colHelper.display({
      id: "ro5",
      header: "Ro5",
      cell: ({ row }) =>
        row.original.lipinski?.passes_ro5 ? (
          <CheckCircle size={14} className="text-emerald-400" />
        ) : (
          <XCircle size={14} className="text-red-400" />
        ),
    }),
    colHelper.display({
      id: "pose",
      header: "Pose",
      cell: ({ row }) =>
        row.original.has_pose ? (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onViewPose(row.original)
            }}
            className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            <Box size={12} /> 3D
          </button>
        ) : (
          <span className="text-slate-600 text-xs">—</span>
        ),
    }),
    colHelper.display({
      id: "expand",
      header: "",
      cell: ({ row }) => (
        <button
          onClick={() => row.toggleExpanded()}
          className="text-slate-500 hover:text-slate-300 transition-colors"
        >
          <ChevronRight
            size={14}
            className={cn(
              "transition-transform",
              row.getIsExpanded() && "rotate-90",
            )}
          />
        </button>
      ),
      size: 32,
    }),
  ]

  const table = useReactTable({
    data: data.results,
    columns,
    state: { sorting, expanded },
    onSortingChange: setSorting,
    onExpandedChange: setExpanded,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    manualPagination: true,
    pageCount: data.total_pages,
  })

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-4 text-xs text-slate-400">
          <span>
            <span className="text-slate-200 font-semibold">
              {data.total_molecules.toLocaleString()}
            </span>{" "}
            total
          </span>
          <span>
            <span className="text-blue-300 font-semibold">
              {data.passed_tier1.toLocaleString()}
            </span>{" "}
            passed Tier 1
          </span>
          <span>
            <span className="text-purple-300 font-semibold">
              {data.passed_tier2.toLocaleString()}
            </span>{" "}
            ML scored
          </span>
          <span>
            <span className="text-emerald-300 font-semibold">
              {data.docked_molecules.toLocaleString()}
            </span>{" "}
            docked
          </span>
        </div>
        <a
          href={exportCsvUrl}
          download
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-xs text-slate-300 transition-colors"
        >
          <Download size={12} /> Export CSV
        </a>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr
                  key={hg.id}
                  className="border-b border-slate-700 bg-slate-800/80"
                >
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 whitespace-nowrap cursor-pointer select-none hover:text-slate-200 transition-colors"
                      onClick={header.column.getToggleSortingHandler()}
                      style={{ width: header.getSize() }}
                    >
                      <div className="flex items-center gap-1">
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                        {header.column.getCanSort() && (
                          <span className="text-slate-600">
                            {header.column.getIsSorted() === "asc" ? (
                              <ChevronUp size={11} className="text-blue-400" />
                            ) : header.column.getIsSorted() === "desc" ? (
                              <ChevronDown
                                size={11}
                                className="text-blue-400"
                              />
                            ) : (
                              <ChevronsUpDown size={11} />
                            )}
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <>
                  <tr
                    key={row.id}
                    className={cn(
                      "border-b border-slate-800 transition-colors cursor-pointer",
                      row.getIsExpanded()
                        ? "bg-slate-800/80"
                        : "hover:bg-slate-800/40",
                    )}
                    onClick={() => row.toggleExpanded()}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-3 py-2.5 align-middle">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </td>
                    ))}
                  </tr>
                  {row.getIsExpanded() && (
                    <tr key={`${row.id}-expanded`} className="bg-slate-900/60">
                      <td colSpan={columns.length} className="px-4 py-4">
                        <MolCard
                          mol={row.original}
                          onSelectPose={
                            row.original.has_pose
                              ? () => onViewPose(row.original)
                              : undefined
                          }
                        />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">
            Page {data.page} of {data.total_pages}
          </p>
          <div className="flex gap-2">
            <button
              disabled={data.page === 1}
              onClick={() => onPageChange(data.page - 1)}
              className="px-3 py-1 rounded bg-slate-700 text-xs text-slate-300 disabled:opacity-40 hover:bg-slate-600 transition-colors"
            >
              Previous
            </button>
            <button
              disabled={data.page === data.total_pages}
              onClick={() => onPageChange(data.page + 1)}
              className="px-3 py-1 rounded bg-slate-700 text-xs text-slate-300 disabled:opacity-40 hover:bg-slate-600 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
