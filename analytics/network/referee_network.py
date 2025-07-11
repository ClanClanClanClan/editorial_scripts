"""
Network analysis for referee relationships and collaboration patterns
"""

import logging
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
import numpy as np
import sqlite3
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
import networkx as nx
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NetworkNode:
    """Represents a referee node in the network"""
    referee_id: str
    name: str
    institution: str
    expertise_areas: List[str]
    performance_score: float
    centrality_measures: Dict[str, float]
    cluster_id: Optional[int] = None


@dataclass
class NetworkEdge:
    """Represents a relationship edge between referees"""
    source: str
    target: str
    weight: float
    edge_type: str  # 'co-review', 'expertise-overlap', 'institutional'
    manuscript_count: int
    last_interaction: datetime


@dataclass
class Community:
    """Represents a community/cluster in the network"""
    id: int
    members: List[str]
    dominant_expertise: List[str]
    avg_performance: float
    internal_density: float
    size: int


class RefereeNetworkAnalyzer:
    """Analyze referee networks and relationships"""
    
    def __init__(self, db_path: str = "data/referees.db"):
        self.db_path = Path(db_path)
        self.network = nx.Graph()
        self._build_network()
    
    def _build_network(self):
        """Build the referee network graph"""
        # Add nodes (referees)
        referees = self._get_all_referees()
        for referee in referees:
            self.network.add_node(
                referee['id'],
                name=referee['name'],
                institution=referee['institution'],
                expertise=referee['expertise_areas'],
                performance=referee['performance_score']
            )
        
        # Add edges (relationships)
        self._add_co_review_edges()
        self._add_expertise_edges()
        self._add_institutional_edges()
    
    def _get_all_referees(self) -> List[Dict]:
        """Get all active referees with their data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    r.id,
                    r.name,
                    r.institution,
                    r.expertise,
                    COALESCE(rm.overall_score, 7.0) as performance_score
                FROM referees r
                LEFT JOIN referee_metrics rm ON r.id = rm.referee_id
                WHERE r.active = 1
            """)
            
            referees = []
            for row in cursor.fetchall():
                referee = dict(row)
                # Parse expertise areas
                if referee['expertise']:
                    import json
                    try:
                        expertise = json.loads(referee['expertise'])
                        referee['expertise_areas'] = list(expertise.keys()) if isinstance(expertise, dict) else expertise
                    except:
                        referee['expertise_areas'] = []
                else:
                    referee['expertise_areas'] = []
                
                referees.append(referee)
            
            return referees
    
    def _add_co_review_edges(self):
        """Add edges between referees who reviewed the same manuscript"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get co-review relationships
            cursor.execute("""
                SELECT 
                    r1.referee_id as referee1,
                    r2.referee_id as referee2,
                    COUNT(*) as manuscript_count,
                    MAX(r1.invited_date) as last_interaction
                FROM review_history r1
                JOIN review_history r2 ON r1.manuscript_id = r2.manuscript_id
                WHERE r1.referee_id < r2.referee_id
                AND r1.decision = 'accepted'
                AND r2.decision = 'accepted'
                GROUP BY r1.referee_id, r2.referee_id
                HAVING manuscript_count >= 2
            """)
            
            for row in cursor.fetchall():
                weight = min(1.0, row[2] / 10)  # Normalize by max expected co-reviews
                
                self.network.add_edge(
                    row[0], row[1],
                    weight=weight,
                    edge_type='co-review',
                    manuscript_count=row[2],
                    last_interaction=row[3]
                )
    
    def _add_expertise_edges(self):
        """Add edges between referees with overlapping expertise"""
        referees = list(self.network.nodes(data=True))
        
        for i, (ref1_id, ref1_data) in enumerate(referees):
            for j in range(i + 1, len(referees)):
                ref2_id, ref2_data = referees[j]
                
                # Calculate expertise overlap
                expertise1 = set(ref1_data.get('expertise', []))
                expertise2 = set(ref2_data.get('expertise', []))
                
                if expertise1 and expertise2:
                    overlap = len(expertise1 & expertise2)
                    total = len(expertise1 | expertise2)
                    
                    if overlap > 0:
                        jaccard_similarity = overlap / total
                        
                        if jaccard_similarity >= 0.3:  # Significant overlap
                            self.network.add_edge(
                                ref1_id, ref2_id,
                                weight=jaccard_similarity,
                                edge_type='expertise-overlap',
                                overlap_count=overlap
                            )
    
    def _add_institutional_edges(self):
        """Add edges between referees from the same institution"""
        referees = list(self.network.nodes(data=True))
        
        for i, (ref1_id, ref1_data) in enumerate(referees):
            for j in range(i + 1, len(referees)):
                ref2_id, ref2_data = referees[j]
                
                inst1 = ref1_data.get('institution', '').lower().strip()
                inst2 = ref2_data.get('institution', '').lower().strip()
                
                if inst1 and inst2 and inst1 == inst2:
                    self.network.add_edge(
                        ref1_id, ref2_id,
                        weight=0.5,  # Moderate weight for institutional connections
                        edge_type='institutional',
                        institution=inst1
                    )
    
    def analyze_network_structure(self) -> Dict:
        """Analyze overall network structure and properties"""
        if self.network.number_of_nodes() == 0:
            return {'error': 'Empty network'}
        
        # Basic metrics
        num_nodes = self.network.number_of_nodes()
        num_edges = self.network.number_of_edges()
        density = nx.density(self.network)
        
        # Connectivity
        is_connected = nx.is_connected(self.network)
        num_components = nx.number_connected_components(self.network)
        
        if is_connected:
            diameter = nx.diameter(self.network)
            avg_path_length = nx.average_shortest_path_length(self.network)
        else:
            # Use largest component
            largest_cc = max(nx.connected_components(self.network), key=len)
            subgraph = self.network.subgraph(largest_cc)
            diameter = nx.diameter(subgraph)
            avg_path_length = nx.average_shortest_path_length(subgraph)
        
        # Clustering
        clustering_coefficient = nx.average_clustering(self.network)
        
        # Centrality measures
        degree_centrality = nx.degree_centrality(self.network)
        betweenness_centrality = nx.betweenness_centrality(self.network)
        closeness_centrality = nx.closeness_centrality(self.network)
        eigenvector_centrality = nx.eigenvector_centrality(self.network, max_iter=1000)
        
        return {
            'basic_metrics': {
                'nodes': num_nodes,
                'edges': num_edges,
                'density': density,
                'clustering_coefficient': clustering_coefficient
            },
            'connectivity': {
                'is_connected': is_connected,
                'num_components': num_components,
                'diameter': diameter,
                'avg_path_length': avg_path_length
            },
            'centrality_stats': {
                'avg_degree_centrality': np.mean(list(degree_centrality.values())),
                'avg_betweenness_centrality': np.mean(list(betweenness_centrality.values())),
                'avg_closeness_centrality': np.mean(list(closeness_centrality.values())),
                'avg_eigenvector_centrality': np.mean(list(eigenvector_centrality.values()))
            },
            'top_central_nodes': self._get_top_central_nodes(
                degree_centrality, betweenness_centrality, 
                closeness_centrality, eigenvector_centrality
            )
        }
    
    def detect_communities(self) -> List[Community]:
        """Detect communities/clusters in the referee network"""
        if self.network.number_of_nodes() < 3:
            return []
        
        # Use Louvain algorithm for community detection
        try:
            import community as community_louvain
            partition = community_louvain.best_partition(self.network)
        except ImportError:
            # Fallback to greedy modularity
            partition = {}
            communities = nx.community.greedy_modularity_communities(self.network)
            for i, community in enumerate(communities):
                for node in community:
                    partition[node] = i
        
        # Analyze each community
        communities = []
        community_groups = defaultdict(list)
        
        for node, comm_id in partition.items():
            community_groups[comm_id].append(node)
        
        for comm_id, members in community_groups.items():
            if len(members) < 2:
                continue
            
            # Get community subgraph
            subgraph = self.network.subgraph(members)
            
            # Calculate metrics
            internal_density = nx.density(subgraph)
            
            # Dominant expertise
            expertise_counter = Counter()
            performance_scores = []
            
            for member in members:
                node_data = self.network.nodes[member]
                expertise = node_data.get('expertise', [])
                expertise_counter.update(expertise)
                performance_scores.append(node_data.get('performance', 7.0))
            
            dominant_expertise = [exp for exp, count in expertise_counter.most_common(3)]
            avg_performance = np.mean(performance_scores)
            
            community = Community(
                id=comm_id,
                members=members,
                dominant_expertise=dominant_expertise,
                avg_performance=avg_performance,
                internal_density=internal_density,
                size=len(members)
            )
            
            communities.append(community)
        
        return sorted(communities, key=lambda c: c.size, reverse=True)
    
    def identify_key_connectors(self, top_k: int = 10) -> List[Dict]:
        """Identify referees who serve as key connectors in the network"""
        if self.network.number_of_nodes() == 0:
            return []
        
        # Calculate various centrality measures
        degree_centrality = nx.degree_centrality(self.network)
        betweenness_centrality = nx.betweenness_centrality(self.network)
        closeness_centrality = nx.closeness_centrality(self.network)
        
        # Calculate bridge importance (nodes whose removal increases components)
        bridge_importance = {}
        original_components = nx.number_connected_components(self.network)
        
        for node in self.network.nodes():
            temp_network = self.network.copy()
            temp_network.remove_node(node)
            new_components = nx.number_connected_components(temp_network)
            bridge_importance[node] = new_components - original_components
        
        # Combine metrics
        connectors = []
        for node in self.network.nodes():
            node_data = self.network.nodes[node]
            
            connector_score = (
                degree_centrality[node] * 0.3 +
                betweenness_centrality[node] * 0.4 +
                closeness_centrality[node] * 0.2 +
                bridge_importance[node] / max(1, original_components) * 0.1
            )
            
            connectors.append({
                'referee_id': node,
                'name': node_data.get('name', 'Unknown'),
                'institution': node_data.get('institution', 'Unknown'),
                'connector_score': connector_score,
                'degree_centrality': degree_centrality[node],
                'betweenness_centrality': betweenness_centrality[node],
                'closeness_centrality': closeness_centrality[node],
                'bridge_importance': bridge_importance[node],
                'num_connections': self.network.degree(node)
            })
        
        return sorted(connectors, key=lambda x: x['connector_score'], reverse=True)[:top_k]
    
    def analyze_expertise_clusters(self) -> Dict:
        """Analyze clustering by expertise areas"""
        expertise_networks = {}
        
        # Create separate networks for each expertise area
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT expertise_area
                FROM referee_expertise
                WHERE confidence_score > 0.5
            """)
            
            expertise_areas = [row[0] for row in cursor.fetchall()]
        
        for expertise in expertise_areas:
            # Get referees with this expertise
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT referee_id, confidence_score
                    FROM referee_expertise
                    WHERE expertise_area = ?
                    AND confidence_score > 0.5
                """, (expertise,))
                
                expertise_referees = cursor.fetchall()
            
            if len(expertise_referees) < 3:
                continue
            
            # Create subgraph
            referee_ids = [r[0] for r in expertise_referees]
            expertise_subgraph = self.network.subgraph(referee_ids)
            
            if expertise_subgraph.number_of_nodes() < 3:
                continue
            
            # Analyze this expertise cluster
            density = nx.density(expertise_subgraph)
            
            # Average confidence in this expertise
            avg_confidence = np.mean([r[1] for r in expertise_referees])
            
            # Clustering coefficient
            clustering = nx.average_clustering(expertise_subgraph)
            
            expertise_networks[expertise] = {
                'num_experts': len(expertise_referees),
                'network_density': density,
                'avg_confidence': avg_confidence,
                'clustering_coefficient': clustering,
                'top_experts': self._get_top_experts_in_area(expertise, expertise_referees)
            }
        
        return expertise_networks
    
    def find_collaboration_opportunities(self, referee_id: str, limit: int = 5) -> List[Dict]:
        """Find potential collaboration opportunities for a referee"""
        if referee_id not in self.network:
            return []
        
        # Get referee's current connections and expertise
        current_neighbors = set(self.network.neighbors(referee_id))
        referee_data = self.network.nodes[referee_id]
        referee_expertise = set(referee_data.get('expertise', []))
        
        # Find potential collaborators
        candidates = []
        
        for node in self.network.nodes():
            if node == referee_id or node in current_neighbors:
                continue
            
            node_data = self.network.nodes[node]
            node_expertise = set(node_data.get('expertise', []))
            
            # Calculate collaboration potential
            expertise_overlap = len(referee_expertise & node_expertise)
            expertise_complement = len(node_expertise - referee_expertise)
            
            # Mutual connections (potential for introduction)
            mutual_connections = len(current_neighbors & set(self.network.neighbors(node)))
            
            # Performance compatibility
            perf_diff = abs(referee_data.get('performance', 7.0) - node_data.get('performance', 7.0))
            
            collaboration_score = (
                expertise_overlap * 2 +  # Shared interests
                expertise_complement * 1.5 +  # Complementary skills
                mutual_connections * 3 +  # Network introduction potential
                max(0, 3 - perf_diff)  # Performance compatibility
            )
            
            if collaboration_score > 3:  # Minimum threshold
                candidates.append({
                    'referee_id': node,
                    'name': node_data.get('name', 'Unknown'),
                    'institution': node_data.get('institution', 'Unknown'),
                    'collaboration_score': collaboration_score,
                    'shared_expertise': list(referee_expertise & node_expertise),
                    'complementary_expertise': list(node_expertise - referee_expertise),
                    'mutual_connections': mutual_connections,
                    'introduction_path': self._find_shortest_path(referee_id, node)
                })
        
        return sorted(candidates, key=lambda x: x['collaboration_score'], reverse=True)[:limit]
    
    def _get_top_central_nodes(self, degree_cent: Dict, between_cent: Dict, 
                              close_cent: Dict, eigen_cent: Dict, top_k: int = 5) -> Dict:
        """Get top nodes by different centrality measures"""
        return {
            'degree': sorted(degree_cent.items(), key=lambda x: x[1], reverse=True)[:top_k],
            'betweenness': sorted(between_cent.items(), key=lambda x: x[1], reverse=True)[:top_k],
            'closeness': sorted(close_cent.items(), key=lambda x: x[1], reverse=True)[:top_k],
            'eigenvector': sorted(eigen_cent.items(), key=lambda x: x[1], reverse=True)[:top_k]
        }
    
    def _get_top_experts_in_area(self, expertise_area: str, 
                                expertise_referees: List[Tuple], top_k: int = 5) -> List[Dict]:
        """Get top experts in a specific area"""
        # Sort by confidence score
        sorted_experts = sorted(expertise_referees, key=lambda x: x[1], reverse=True)
        
        top_experts = []
        for referee_id, confidence in sorted_experts[:top_k]:
            if referee_id in self.network:
                node_data = self.network.nodes[referee_id]
                top_experts.append({
                    'referee_id': referee_id,
                    'name': node_data.get('name', 'Unknown'),
                    'confidence': confidence,
                    'centrality': nx.degree_centrality(self.network).get(referee_id, 0)
                })
        
        return top_experts
    
    def _find_shortest_path(self, source: str, target: str) -> List[str]:
        """Find shortest path between two referees"""
        try:
            path = nx.shortest_path(self.network, source, target)
            return path
        except nx.NetworkXNoPath:
            return []
    
    def analyze_referee_position(self, referee_id: str) -> Dict:
        """Analyze a specific referee's position in the network"""
        if referee_id not in self.network:
            return {'error': 'Referee not found in network'}
        
        # Centrality measures
        degree_cent = nx.degree_centrality(self.network)[referee_id]
        between_cent = nx.betweenness_centrality(self.network)[referee_id]
        close_cent = nx.closeness_centrality(self.network)[referee_id]
        eigen_cent = nx.eigenvector_centrality(self.network, max_iter=1000)[referee_id]
        
        # Local network properties
        neighbors = list(self.network.neighbors(referee_id))
        local_subgraph = self.network.subgraph([referee_id] + neighbors)
        local_clustering = nx.clustering(self.network, referee_id)
        
        # Structural holes (Burt's constraint)
        constraint = self._calculate_constraint(referee_id)
        
        # Expertise diversity of connections
        neighbor_expertise = []
        for neighbor in neighbors:
            neighbor_data = self.network.nodes[neighbor]
            neighbor_expertise.extend(neighbor_data.get('expertise', []))
        
        expertise_diversity = len(set(neighbor_expertise))
        
        return {
            'centrality_measures': {
                'degree': degree_cent,
                'betweenness': between_cent,
                'closeness': close_cent,
                'eigenvector': eigen_cent
            },
            'local_properties': {
                'num_connections': len(neighbors),
                'local_clustering': local_clustering,
                'constraint': constraint,
                'expertise_diversity': expertise_diversity
            },
            'network_role': self._classify_network_role(
                degree_cent, between_cent, local_clustering, constraint
            ),
            'influence_score': self._calculate_influence_score(
                degree_cent, between_cent, eigen_cent
            )
        }
    
    def _calculate_constraint(self, node: str) -> float:
        """Calculate Burt's structural constraint for a node"""
        neighbors = list(self.network.neighbors(node))
        
        if len(neighbors) <= 1:
            return 1.0
        
        constraint = 0.0
        for neighbor in neighbors:
            # Direct constraint
            tie_strength = self.network[node][neighbor].get('weight', 1.0)
            normalized_strength = tie_strength / sum(
                self.network[node][n].get('weight', 1.0) for n in neighbors
            )
            
            # Indirect constraint through mutual connections
            mutual = set(self.network.neighbors(neighbor)) & set(neighbors)
            indirect = sum(
                (self.network[node][mutual_neighbor].get('weight', 1.0) *
                 self.network[neighbor][mutual_neighbor].get('weight', 1.0))
                for mutual_neighbor in mutual
            )
            
            node_constraint = (normalized_strength + indirect) ** 2
            constraint += node_constraint
        
        return constraint
    
    def _classify_network_role(self, degree_cent: float, between_cent: float, 
                              clustering: float, constraint: float) -> str:
        """Classify the network role of a referee"""
        if between_cent > 0.1 and constraint < 0.3:
            return "broker"  # High betweenness, low constraint
        elif degree_cent > 0.1 and clustering > 0.5:
            return "hub"  # High degree, high clustering
        elif clustering > 0.7:
            return "cluster_member"  # High clustering
        elif degree_cent > 0.05:
            return "connector"  # Moderate degree
        else:
            return "peripheral"  # Low connectivity
    
    def _calculate_influence_score(self, degree_cent: float, between_cent: float, 
                                  eigen_cent: float) -> float:
        """Calculate overall influence score"""
        return (degree_cent * 0.3 + between_cent * 0.4 + eigen_cent * 0.3)
    
    def get_network_statistics(self) -> Dict:
        """Get comprehensive network statistics"""
        structure = self.analyze_network_structure()
        communities = self.detect_communities()
        connectors = self.identify_key_connectors()
        expertise_clusters = self.analyze_expertise_clusters()
        
        return {
            'structure': structure,
            'communities': [
                {
                    'id': c.id,
                    'size': c.size,
                    'dominant_expertise': c.dominant_expertise,
                    'avg_performance': c.avg_performance,
                    'internal_density': c.internal_density
                }
                for c in communities
            ],
            'key_connectors': connectors,
            'expertise_clusters': expertise_clusters,
            'summary': {
                'total_referees': self.network.number_of_nodes(),
                'total_connections': self.network.number_of_edges(),
                'num_communities': len(communities),
                'avg_community_size': np.mean([c.size for c in communities]) if communities else 0,
                'network_cohesion': structure['basic_metrics']['clustering_coefficient']
            }
        }