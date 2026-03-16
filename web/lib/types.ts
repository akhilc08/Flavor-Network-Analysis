export type PairingLabel = 'Surprising' | 'Unexpected' | 'Classic'

export interface Pairing {
  name: string
  pairing_score: number
  surprise_score: number
  label: PairingLabel
  shared_molecules: string[]
}

export interface SearchResponse {
  ingredient: string
  pairings: Pairing[]
}

export interface UncertainPair {
  pair_id: string
  ingredient_a: string
  ingredient_b: string
  score: number
  uncertainty: number
  shared_molecules: string[]
}

export interface UncertainPairsResponse {
  auc: number
  pairs: UncertainPair[]
}

export interface RateRequest {
  ratings: { ingredient_a: string; ingredient_b: string; rating: number }[]
}

export interface RateResponse {
  auc_before: number
  auc_after: number
  delta: number
}

export interface GraphNode {
  id: string
  label: string
  size: number
  center: boolean
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
  label: PairingLabel
  color: string
}

export interface GraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface RecipeRequest {
  ingredients: string[]
  shared_molecules: string[]
  flavor_labels: Record<string, string>
}
