"""
Cross-document analyzer for consistency checks.
File: backend/app/analyzers/cross_document_analyzer.py
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher

from app.services.rag_service import rag_service
from app.schemas.analysis import RiskFindingCreate, NegotiationPointCreate

logger = logging.getLogger(__name__)


class CrossDocumentAnalyzer:
    """
    Analyzer for cross-document consistency.
    Compares information across multiple documents.
    """
    
    def __init__(self):
        """Initialize cross-document analyzer."""
        self.fields_to_compare = [
            'seller_name',
            'buyer_name',
            'property_description',
            'property_address',
            'purchase_price',
            'date'
        ]
    
    async def analyze(
        self,
        documents: List[Dict[str, Any]],
        namespace: str
    ) -> Tuple[List[RiskFindingCreate], List[NegotiationPointCreate]]:
        """
        Analyze consistency across documents.
        
        Args:
            documents: List of documents with their extracted info
            namespace: Pinecone namespace
        
        Returns:
            Tuple of (risks, negotiation_points)
        """
        risks = []
        negotiation_points = []
        
        try:
            if len(documents) < 2:
                return risks, negotiation_points
            
            # Step 1: Extract key information from each document
            doc_info = {}
            for doc in documents:
                info = await self._extract_document_info(doc)
                doc_info[doc['document_id']] = {
                    'type': doc.get('document_type'),
                    'info': info,
                    'text': doc.get('extracted_text', '')[:1000]  # First 1000 chars
                }
            
            # Step 2: Compare information across documents
            comparison_risks = await self._compare_information(doc_info)
            risks.extend(comparison_risks)
            
            # Step 3: Check for logical consistency
            logical_risks = await self._check_logical_consistency(doc_info)
            risks.extend(logical_risks)
            
            # Step 4: Check chronological order
            chronological_risks = await self._check_chronological_order(doc_info)
            risks.extend(chronological_risks)
            
            # Step 5: Generate negotiation points
            negotiation_points = await self._generate_negotiation_points(risks)
            
            # Step 6: Use RAG for deep analysis
            rag_risks = await self._rag_analysis(documents, namespace)
            risks.extend(rag_risks)
            
        except Exception as e:
            logger.error(f"Cross-document analysis failed: {str(e)}")
        
        return risks, negotiation_points
    
    async def _extract_document_info(
        self,
        document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract key information from a document."""
        info = {
            'seller_name': None,
            'buyer_name': None,
            'property_description': None,
            'property_address': None,
            'purchase_price': None,
            'date': None,
            'registration_number': None,
            'area': None
        }
        
        text = document.get('extracted_text', '').lower()
        
        # Extract names (simplified)
        name_patterns = [
            (r'seller[:\s]+([A-Za-z\s]+)', 'seller_name'),
            (r'vendor[:\s]+([A-Za-z\s]+)', 'seller_name'),
            (r'buyer[:\s]+([A-Za-z\s]+)', 'buyer_name'),
            (r'purchaser[:\s]+([A-Za-z\s]+)', 'buyer_name'),
            (r'registered owner[:\s]+([A-Za-z\s]+)', 'seller_name')
        ]
        
        for pattern, field in name_patterns:
            import re
            match = re.search(pattern, text, re.IGNORECASE)
            if match and not info[field]:
                info[field] = match.group(1).strip()
        
        # Extract price
        price_patterns = [
            r'purchase price[:\s]*\$?([\d,]+(?:\.\d{2})?)',
            r'sale price[:\s]*\$?([\d,]+(?:\.\d{2})?)',
            r'consideration[:\s]*\$?([\d,]+(?:\.\d{2})?)'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['purchase_price'] = match.group(1)
                break
        
        return info
    
    async def _compare_information(
        self,
        doc_info: Dict[str, Dict]
    ) -> List[RiskFindingCreate]:
        """Compare information across documents."""
        risks = []
        
        # Get all document IDs
        doc_ids = list(doc_info.keys())
        
        # Compare each field
        for field in self.fields_to_compare:
            values = {}
            for doc_id, data in doc_info.items():
                value = data['info'].get(field)
                if value:
                    values[doc_id] = value
            
            # Check if we have multiple values to compare
            if len(values) >= 2:
                # Check if all values are consistent
                first_value = list(values.values())[0]
                inconsistent_docs = []
                
                for doc_id, value in values.items():
                    if not self._values_match(first_value, value):
                        inconsistent_docs.append(doc_id)
                
                if inconsistent_docs:
                    doc_types = [doc_info[doc_id]['type'] for doc_id in values.keys()]
                    
                    risks.append(
                        RiskFindingCreate(
                            category='inconsistency',
                            severity='high' if field in ['seller_name', 'purchase_price'] else 'medium',
                            title=f'Inconsistent {field.replace("_", " ").title()}',
                            description=f'The {field.replace("_", " ")} differs across documents: {values}',
                            recommendation=f'Verify the correct {field.replace("_", " ")} with the seller and ensure all documents are updated.',
                            confidence=0.8
                        )
                    )
        
        return risks
    
    async def _check_logical_consistency(
        self,
        doc_info: Dict[str, Dict]
    ) -> List[RiskFindingCreate]:
        """Check for logical inconsistencies."""
        risks = []
        
        # Check if seller in title matches seller in contract
        seller_values = {}
        buyer_values = {}
        
        for doc_id, data in doc_info.items():
            if data['type'] == 'title_deed' and data['info'].get('seller_name'):
                seller_values['title'] = data['info']['seller_name']
            elif data['type'] == 'sale_agreement':
                if data['info'].get('seller_name'):
                    seller_values['contract'] = data['info']['seller_name']
                if data['info'].get('buyer_name'):
                    buyer_values['contract'] = data['info']['buyer_name']
        
        # Check seller consistency
        if 'title' in seller_values and 'contract' in seller_values:
            if not self._names_match(seller_values['title'], seller_values['contract']):
                risks.append(
                    RiskFindingCreate(
                        category='inconsistency',
                        severity='critical',
                        title='Seller Name Mismatch',
                        description=f'Seller name in title deed ({seller_values["title"]}) does not match seller in contract ({seller_values["contract"]})',
                        recommendation='Verify the correct owner and ensure the contract is signed by the registered owner.',
                        confidence=0.9
                    )
                )
        
        return risks
    
    async def _check_chronological_order(
        self,
        doc_info: Dict[str, Dict]
    ) -> List[RiskFindingCreate]:
        """Check if documents are in correct chronological order."""
        risks = []
        
        # Extract dates from documents
        dates = []
        for doc_id, data in doc_info.items():
            if data['info'].get('date'):
                dates.append({
                    'doc_id': doc_id,
                    'doc_type': data['type'],
                    'date': data['info']['date']
                })
        
        if len(dates) >= 2:
            # Title deed should be before sale agreement
            title_date = None
            contract_date = None
            
            for d in dates:
                if d['doc_type'] == 'title_deed':
                    title_date = d
                elif d['doc_type'] == 'sale_agreement':
                    contract_date = d
            
            if title_date and contract_date:
                # Simple string comparison - would need proper date parsing in production
                if title_date['date'] > contract_date['date']:
                    risks.append(
                        RiskFindingCreate(
                            category='inconsistency',
                            severity='medium',
                            title='Chronological Issue',
                            description='The title deed date is after the sale agreement date, which is unusual.',
                            recommendation='Verify the correct dates and ensure the title was valid at time of sale.',
                            confidence=0.6
                        )
                    )
        
        return risks
    
    async def _generate_negotiation_points(
        self,
        risks: List[RiskFindingCreate]
    ) -> List[NegotiationPointCreate]:
        """Generate negotiation points from inconsistencies."""
        points = []
        
        # Critical inconsistencies
        critical_inconsistencies = [r for r in risks if r.severity == 'critical']
        if critical_inconsistencies:
            points.append(
                NegotiationPointCreate(
                    point_type='condition',
                    title='Critical Document Inconsistencies',
                    description=f'Found {len(critical_inconsistencies)} critical inconsistencies between documents.',
                    leverage_level='high',
                    estimated_impact='Transaction cannot proceed without resolution',
                    suggested_action='Pause the transaction until all critical inconsistencies are resolved and documents are corrected.'
                )
            )
        
        # Price inconsistencies
        price_inconsistencies = [r for r in risks if 'price' in r.title.lower()]
        if price_inconsistencies:
            points.append(
                NegotiationPointCreate(
                    point_type='price',
                    title='Price Information Inconsistent',
                    description='The purchase price is not consistent across documents.',
                    leverage_level='high',
                    estimated_impact='Could lead to disputes or incorrect tax payments',
                    suggested_action='Clarify the exact purchase price and ensure all documents reflect the same amount.'
                )
            )
        
        return points
    
    async def _rag_analysis(
        self,
        documents: List[Dict[str, Any]],
        namespace: str
    ) -> List[RiskFindingCreate]:
        """Use RAG for cross-document analysis."""
        risks = []
        
        try:
            # Create a combined query
            query = "Compare these documents and identify any inconsistencies or contradictions."
            
            # Search across all documents
            all_docs = []
            for doc in documents:
                docs = await rag_service.similarity_search(
                    query=query,
                    namespace=namespace,
                    k=2,
                    filter={'document_id': doc['document_id']}
                )
                all_docs.extend(docs)
            
            if all_docs:
                result = await rag_service.analyze_with_context(
                    query=query,
                    context_docs=all_docs,
                    analysis_type="cross_document"
                )
                
                # Parse response for inconsistencies (simplified)
                if "inconsist" in result['response'].lower() or "contradict" in result['response'].lower():
                    risks.append(
                        RiskFindingCreate(
                            category='inconsistency',
                            severity='medium',
                            title='AI-Detected Inconsistencies',
                            description=result['response'][:200],
                            recommendation='Review these potential inconsistencies with a legal professional.',
                            confidence=0.6
                        )
                    )
        
        except Exception as e:
            logger.error(f"RAG analysis failed: {str(e)}")
        
        return risks
    
    def _values_match(self, val1: str, val2: str, threshold: float = 0.8) -> bool:
        """Check if two values match (with fuzzy matching)."""
        if not val1 or not val2:
            return False
        
        val1 = val1.lower().strip()
        val2 = val2.lower().strip()
        
        # Exact match
        if val1 == val2:
            return True
        
        # Fuzzy match
        ratio = SequenceMatcher(None, val1, val2).ratio()
        return ratio >= threshold
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if names match (considering common variations)."""
        if not name1 or not name2:
            return False
        
        # Remove common titles and normalize
        titles = ['mr', 'mrs', 'ms', 'dr', 'prof']
        
        def normalize(name):
            name = name.lower().strip()
            for title in titles:
                if name.startswith(title + ' '):
                    name = name[len(title)+1:]
            return name.strip()
        
        return self._values_match(normalize(name1), normalize(name2), 0.85)

# Create singleton instance
cross_document_analyzer = CrossDocumentAnalyzer()
