import React, { useMemo } from 'react'
import ReactFlow, {
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from 'reactflow'
import dagre from '@dagrejs/dagre'
import 'reactflow/dist/style.css'

const NODE_WIDTH  = 188
const NODE_HEIGHT = 76
const PADDING     = 56

function CourseNode({ data }) {
  return (
    <div
      style={{
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        background: '#002A5C',
        border: '2px solid #4a90d9',
        borderRadius: '4px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '8px 12px',
        textAlign: 'center',
        boxShadow: '0 2px 10px rgba(0, 42, 92, 0.4)',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#4a90d9', border: 'none', width: 8, height: 8 }} />
      <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#ffffff', fontSize: '12px', lineHeight: 1 }}>
        {data.code}
      </span>
      <span style={{ color: 'rgba(255,255,255,0.75)', fontSize: '10px', lineHeight: 1.3, marginTop: '6px', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', maxWidth: '160px' }}>
        {data.name}
      </span>
      <Handle type="source" position={Position.Bottom} style={{ background: '#4a90d9', border: 'none', width: 8, height: 8 }} />
    </div>
  )
}

const nodeTypes = { courseNode: CourseNode }

function applyDagreLayout(nodes, edges) {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'BT', ranksep: 90, nodesep: 48, marginx: 24, marginy: 24 })
  nodes.forEach(n => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }))
  edges.forEach(e => g.setEdge(e.source, e.target))
  dagre.layout(g)
  return nodes.map(n => {
    const pos = g.node(n.id)
    return { ...n, position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 } }
  })
}

function flattenCourse(course, nodes, edges, visited = new Set()) {
  if (visited.has(course.code)) return
  visited.add(course.code)
  nodes.push({ id: course.code, type: 'courseNode', data: { code: course.code, name: course.name }, position: { x: 0, y: 0 } })
  if (course.prerequisites && course.prerequisites.length > 0) {
    course.prerequisites.forEach(prereq => {
      edges.push({
        id: `${prereq.code}→${course.code}`,
        source: prereq.code,
        target: course.code,
        type: 'step',
        markerEnd: { type: MarkerType.ArrowClosed, color: '#4a90d9', width: 16, height: 16 },
        style: { stroke: '#4a90d9', strokeWidth: 2 },
      })
      flattenCourse(prereq, nodes, edges, visited)
    })
  }
}

export default function FlowVisualizer({ courseData }) {
  const { initialNodes, initialEdges, containerHeight } = useMemo(() => {
    const nodes = []
    const edges = []
    flattenCourse(courseData, nodes, edges)
    const laidOutNodes = applyDagreLayout(nodes, edges)

    if (laidOutNodes.length === 0) {
      return { initialNodes: [], initialEdges: [], containerHeight: window.innerHeight }
    }

    const xs = laidOutNodes.map(n => n.position.x)
    const ys = laidOutNodes.map(n => n.position.y)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs) + NODE_WIDTH
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys) + NODE_HEIGHT
    const treeWidth  = maxX - minX
    const treeHeight = maxY - minY

    // Center horizontally within the viewport
    const offsetX = Math.max(PADDING, (window.innerWidth - treeWidth) / 2) - minX
    const offsetY = PADDING - minY

    const centeredNodes = laidOutNodes.map(n => ({
      ...n,
      position: { x: n.position.x + offsetX, y: n.position.y + offsetY },
    }))

    return {
      initialNodes: centeredNodes,
      initialEdges: edges,
      containerHeight: Math.max(window.innerHeight, treeHeight + PADDING * 2),
    }
  }, [courseData])

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  return (
    <div style={{ width: '100%', height: containerHeight }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        panOnDrag={false}
        panOnScroll={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        preventScrolling={false}
        fitView={false}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        style={{ background: 'transparent' }}
        proOptions={{ hideAttribution: true }}
      />
    </div>
  )
}
