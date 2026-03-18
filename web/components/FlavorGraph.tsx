'use client'

import { useEffect } from 'react'
import Graph from 'graphology'
import { SigmaContainer, useLoadGraph, useRegisterEvents } from '@react-sigma/core'
import '@react-sigma/core/lib/style.css'
import type { GraphResponse } from '@/lib/types'

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
      graph.addEdge(edge.source, edge.target, {
        size: Math.max(1, edge.weight * 3),
        color: edge.color,
        label: edge.label,
      })
    })
    loadGraph(graph)

    return () => {
      graph.clear()
    }
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
  return (
    <SigmaContainer
      graph={Graph}
      style={{ width: '100%', height: '500px' }}
      settings={{ renderEdgeLabels: false, defaultEdgeType: 'line' }}
    >
      <GraphLoader data={data} />
      <NodeClickHandler onNodeClick={onNodeClick} />
    </SigmaContainer>
  )
}
