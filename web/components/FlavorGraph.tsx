'use client'

import { useEffect } from 'react'
import Graph from 'graphology'
import { SigmaContainer, useLoadGraph } from '@react-sigma/core'
import '@react-sigma/core/lib/style.css'
import type { GraphResponse } from '@/lib/types'

function GraphLoader({ data }: { data: GraphResponse }) {
  const loadGraph = useLoadGraph()

  useEffect(() => {
    const graph = new Graph()
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
  }, [data, loadGraph])

  return null
}

export default function FlavorGraph({ data }: { data: GraphResponse }) {
  return (
    <SigmaContainer
      graph={Graph}
      style={{ width: '100%', height: '500px' }}
      settings={{ renderEdgeLabels: true, defaultEdgeType: 'arrow' }}
    >
      <GraphLoader data={data} />
    </SigmaContainer>
  )
}
