'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import Graph from 'graphology'
import { SigmaContainer, useLoadGraph, useRegisterEvents } from '@react-sigma/core'
import '@react-sigma/core/lib/style.css'
import type { GraphResponse } from '@/lib/types'

type Tooltip = { visible: false } | { visible: true; x: number; y: number; lines: string[] }

function NodeClickHandler({ onNodeClick }: { onNodeClick?: (nodeId: string) => void }) {
  const registerEvents = useRegisterEvents()

  useEffect(() => {
    if (!onNodeClick) return
    registerEvents({
      clickNode: ({ node }) => onNodeClick(node),
    })
  }, [registerEvents, onNodeClick])

  return null
}

function HoverHandler({
  data,
  mousePos,
  onTooltip,
}: {
  data: GraphResponse
  mousePos: React.MutableRefObject<{ x: number; y: number }>
  onTooltip: (tooltip: Tooltip) => void
}) {
  const registerEvents = useRegisterEvents()
  const centerNode = data.nodes.find(n => n.center)

  useEffect(() => {
    registerEvents({
      enterNode: ({ node }) => {
        const nodeInfo = data.nodes.find(n => n.id === node)
        const lines: string[] = [nodeInfo?.label ?? node]

        if (centerNode && node !== centerNode.id) {
          const edge = data.edges.find(e =>
            (e.source === node && e.target === centerNode.id) ||
            (e.target === node && e.source === centerNode.id)
          )
          if (edge) {
            lines.push(`Pairing score: ${edge.weight.toFixed(3)}`)
            lines.push(edge.label)
          }
        } else if (centerNode && node === centerNode.id) {
          lines.push('Center ingredient')
        }

        onTooltip({ visible: true, x: mousePos.current.x, y: mousePos.current.y, lines })
      },
      leaveNode: () => onTooltip({ visible: false }),
      enterEdge: ({ edge }) => {
        const [source, target] = edge.split('||')
        const edgeData = data.edges.find(e =>
          (e.source === source && e.target === target) ||
          (e.source === target && e.target === source)
        )
        if (!edgeData) { onTooltip({ visible: false }); return }
        onTooltip({
          visible: true,
          x: mousePos.current.x,
          y: mousePos.current.y,
          lines: [
            `${edgeData.source} ↔ ${edgeData.target}`,
            `Score: ${edgeData.weight.toFixed(3)}`,
            edgeData.label,
          ],
        })
      },
      leaveEdge: () => onTooltip({ visible: false }),
    })
  }, [registerEvents, data, centerNode, mousePos, onTooltip])

  return null
}

function GraphLoader({ data }: { data: GraphResponse }) {
  const loadGraph = useLoadGraph()

  useEffect(() => {
    const graph = new Graph()
    graph.clear()
    data.nodes.forEach(node => {
      graph.addNode(node.id, {
        label: node.label,
        size: node.size,
        color: node.center ? '#c4622a' : '#a08060',
        x: Math.random(),
        y: Math.random(),
      })
    })
    data.edges.forEach(edge => {
      graph.addEdgeWithKey(`${edge.source}||${edge.target}`, edge.source, edge.target, {
        size: Math.max(1, edge.weight * 3),
        color: edge.color,
        label: edge.label,
        weight: edge.weight,
      })
    })
    loadGraph(graph)

    return () => { graph.clear() }
  }, [data, loadGraph])

  return null
}

export default function FlavorGraph({
  data,
  onNodeClick,
}: {
  data: GraphResponse
  onNodeClick?: (nodeId: string) => void
}) {
  const [tooltip, setTooltip] = useState<Tooltip>({ visible: false })
  const mousePos = useRef({ x: 0, y: 0 })

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    mousePos.current = { x: e.clientX - rect.left, y: e.clientY - rect.top }
    setTooltip(prev =>
      prev.visible ? { ...prev, x: mousePos.current.x, y: mousePos.current.y } : prev
    )
  }, [])

  return (
    <div style={{ position: 'relative' }} onMouseMove={handleMouseMove}>
      <SigmaContainer
        graph={Graph}
        style={{ width: '100%', height: '500px' }}
        settings={{ renderEdgeLabels: false, defaultEdgeType: 'line' }}
      >
        <GraphLoader data={data} />
        <NodeClickHandler onNodeClick={onNodeClick} />
        <HoverHandler data={data} mousePos={mousePos} onTooltip={setTooltip} />
      </SigmaContainer>
      {tooltip.visible && (
        <div
          style={{
            position: 'absolute',
            left: tooltip.x + 14,
            top: tooltip.y + 14,
            background: 'rgba(36, 26, 16, 0.93)',
            color: '#f5ede0',
            padding: '8px 12px',
            borderRadius: 8,
            fontSize: 13,
            fontFamily: 'system-ui, sans-serif',
            pointerEvents: 'none',
            boxShadow: '0 2px 10px rgba(0,0,0,0.35)',
            zIndex: 10,
            lineHeight: 1.6,
            whiteSpace: 'nowrap',
          }}
        >
          {tooltip.lines.map((line, i) => (
            <div key={i} style={i === 0 ? { fontWeight: 600 } : { opacity: 0.8, fontSize: 12 }}>
              {line}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
