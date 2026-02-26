"""
Sale agreement analyzer for contract clause analysis.
File: backend/app/analyzers/contract_analyzer.py
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from app.services.rag_service import rag_service
from app.schemas.analysis import RiskFindingCreate, NegotiationPointCreate

logger = logging.getLogger(__name__)


class ContractAnalyzer:
    """
    Analyzer for sale agreements and contracts.
    Identifies risky clauses, missing terms, and unfair provisions.
    """
    
    def __init__(self):
        """Initialize contract analyzer."""
        self.required_clauses = [
            'parties',
            'property description',
            'purchase price',
            'payment terms',
            'possession date',
            'representations and warranties',
            'default',
            'dispute resolution',
            'governing law'
        ]
        
        self.risky_clause_patterns = {
            'as_is': [
                r'as is',
                r'where is',
                r'with all faults'
            ],
            'no_warranty': [
                r'without (any )?warranty',
                r'disclaims? all warranties'
            ],
            'unilateral_termination': [
                r'(seller|buyer) may terminate.*?(without cause|at (his|its) sole discretion)',
                r'unilateral right to cancel'
            ],
            'hidden_fees': [
                r'additional (fees?|charges|costs)',
                r'buyer shall pay all (costs|expenses)',
                r'processing fee'
            ],
            'short_inspection': [
                r'inspection period of \d+ (days?|hours?)',
                r'inspection.*?within \d+ (days?|hours?)'
            ],
            'binding_arbitration': [
                r'mandatory arbitration',
                r'binding arbitration',
                r'waive (right to )?court'
            ]
        }
        
        self.missing_clause_risks = {
            'inspection': 'No inspection contingency found - you may lose the right to inspect the property',
            'financing': 'No financing contingency - you may lose deposit if loan fails',
            'title': 'No title contingency - you may be stuck if title issues arise',
            'disclosure': 'No seller disclosure requirements mentioned'
        }
    
    async def analyze(
        self,
        document_id: str,
        document_text: str,
        namespace: str
    ) -> Tuple[List[RiskFindingCreate], List[NegotiationPointCreate]]:
        """
        Analyze contract for risks.
        
        Args:
            document_id: Document ID
            document_text: Extracted text from document
            namespace: Pinecone namespace
        
        Returns:
            Tuple of (risks, negotiation_points)
        """
        risks = []
        negotiation_points = []
        
        try:
            # Step 1: Extract key terms
            terms = await self._extract_contract_terms(document_text)
            
            # Step 2: Check for missing required clauses
            missing_risks = await self._check_missing_clauses(terms)
            risks.extend(missing_risks)
            
            # Step 3: Check for risky clauses
            clause_risks = await self._check_risky_clauses(document_text)
            risks.extend(clause_risks)
            
            # Step 4: Check payment terms
            payment_risks = await self._check_payment_terms(terms, document_text)
            risks.extend(payment_risks)
            
            # Step 5: Check dates and timelines
            date_risks = await self._check_dates(document_text)
            risks.extend(date_risks)
            
            # Step 6: Generate negotiation points
            negotiation_points = await self._generate_negotiation_points(
                risks, terms, document_text
            )
            
            # Step 7: Use RAG for deep analysis
            rag_risks = await self._rag_analysis(document_id, namespace)
            risks.extend(rag_risks)
            
        except Exception as e:
            logger.error(f"Contract analysis failed: {str(e)}")
        
        return risks, negotiation_points
    
    async def _extract_contract_terms(self, text: str) -> Dict[str, Any]:
        """Extract key terms from contract."""
        terms = {
            'parties': [],
            'property_description': '',
            'purchase_price': '',
            'payment_terms': [],
            'possession_date': '',
            'closing_date': '',
            'earnest_money': '',
            'contingencies': []
        }
        
        # Extract parties (buyer and seller)
        party_patterns = [
            r'(buyer|purchaser)[:\s]+([A-Za-z\s,]+)',
            r'(seller|vendor)[:\s]+([A-Za-z\s,]+)',
            r'between\s+([A-Za-z\s]+)\s+and\s+([A-Za-z\s]+)'
        ]
        
        for pattern in party_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    terms['parties'].extend([m for m in match if m and len(m) > 3])
                else:
                    terms['parties'].append(match)
        
        # Extract purchase price
        price_patterns = [
            r'purchase price[:\s]*\$?([\d,]+(?:\.\d{2})?)',
            r'sale price[:\s]*\$?([\d,]+(?:\.\d{2})?)',
            r'price[:\s]*\$?([\d,]+(?:\.\d{2})?)',
            r'total consideration[:\s]*\$?([\d,]+(?:\.\d{2})?)'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                terms['purchase_price'] = match.group(1)
                break
        
        # Extract dates
        date_patterns = [
            r'possession date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'closing date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'date of closing[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'possession' in pattern:
                    terms['possession_date'] = match.group(1)
                else:
                    terms['closing_date'] = match.group(1)
        
        return terms
    
    async def _check_missing_clauses(
        self,
        terms: Dict[str, Any]
    ) -> List[RiskFindingCreate]:
        """Check for missing required clauses."""
        risks = []
        
        # Check each required clause
        for clause in self.required_clauses:
            found = False
            
            if clause == 'parties' and terms['parties']:
                found = True
            elif clause == 'property description' and terms['property_description']:
                found = True
            elif clause == 'purchase price' and terms['purchase_price']:
                found = True
            elif clause == 'possession date' and terms['possession_date']:
                found = True
            else:
                # Generic check for clause in text
                # This is simplified - would need better detection
                pass
            
            if not found:
                risk_info = self.missing_clause_risks.get(clause.split()[0])
                
                risks.append(
                    RiskFindingCreate(
                        category='contract',
                        severity='high' if clause in ['parties', 'purchase price'] else 'medium',
                        title=f'Missing {clause.title()} Clause',
                        description=risk_info or f'The contract does not contain a clear {clause} clause.',
                        recommendation=f'Ensure the contract includes a clear {clause} clause before signing.',
                        confidence=0.8
                    )
                )
        
        return risks
    
    async def _check_risky_clauses(self, text: str) -> List[RiskFindingCreate]:
        """Check for risky or unfair clauses."""
        risks = []
        
        for risk_type, patterns in self.risky_clause_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    context = self._extract_context(text, pattern, 150)
                    
                    if risk_type == 'as_is':
                        risks.append(
                            RiskFindingCreate(
                                category='contract',
                                severity='high',
                                title='"As Is" Clause Detected',
                                description='The property is being sold "as is" without seller repairs.',
                                recommendation='Get a thorough inspection and consider negotiating a credit for necessary repairs.',
                                location_ref=self._find_location(text, pattern),
                                quoted_text=context,
                                confidence=0.9
                            )
                        )
                    
                    elif risk_type == 'unilateral_termination':
                        risks.append(
                            RiskFindingCreate(
                                category='contract',
                                severity='critical',
                                title='Unilateral Termination Right',
                                description='One party has the right to terminate without cause, which is unfair.',
                                recommendation='Negotiate for mutual termination rights or remove this clause.',
                                location_ref=self._find_location(text, pattern),
                                quoted_text=context,
                                confidence=0.8
                            )
                        )
                    
                    elif risk_type == 'hidden_fees':
                        risks.append(
                            RiskFindingCreate(
                                category='contract',
                                severity='medium',
                                title='Potential Hidden Fees',
                                description='The contract mentions additional fees or costs.',
                                recommendation='Request a complete breakdown of all fees and who pays them.',
                                location_ref=self._find_location(text, pattern),
                                quoted_text=context,
                                confidence=0.7
                            )
                        )
        
        return risks
    
    async def _check_payment_terms(
        self,
        terms: Dict[str, Any],
        text: str
    ) -> List[RiskFindingCreate]:
        """Check payment terms for risks."""
        risks = []
        
        # Check for earnest money
        earnest_patterns = [
            r'earnest money[:\s]*\$?([\d,]+)',
            r'deposit[:\s]*\$?([\d,]+)',
            r'good faith deposit[:\s]*\$?([\d,]+)'
        ]
        
        earnest_found = False
        for pattern in earnest_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                earnest_found = True
                break
        
        if not earnest_found:
            risks.append(
                RiskFindingCreate(
                    category='contract',
                    severity='medium',
                    title='Earnest Money Not Specified',
                    description='The contract does not specify the earnest money deposit amount.',
                    recommendation='Ensure the earnest money amount and terms are clearly stated.',
                    confidence=0.7
                )
            )
        
        # Check for payment schedule
        if 'down payment' in text.lower() or 'installment' in text.lower():
            # Payment schedule exists - check if clear
            if 'schedule' not in text.lower() and 'timeline' not in text.lower():
                risks.append(
                    RiskFindingCreate(
                        category='contract',
                        severity='medium',
                        title='Unclear Payment Schedule',
                        description='Payment installments are mentioned but no clear schedule is provided.',
                        recommendation='Request a detailed payment schedule with dates and amounts.',
                        confidence=0.6
                    )
                )
        
        return risks
    
    async def _check_dates(self, text: str) -> List[RiskFindingCreate]:
        """Check dates and timelines for risks."""
        risks = []
        
        # Look for short inspection periods
        inspection_pattern = r'inspection.*?(\d+)\s*(day|hour)'
        match = re.search(inspection_pattern, text, re.IGNORECASE)
        
        if match:
            days = int(match.group(1))
            unit = match.group(2)
            
            if (unit.startswith('day') and days < 5) or (unit.startswith('hour') and days < 24):
                risks.append(
                    RiskFindingCreate(
                        category='contract',
                        severity='high',
                        title=f'Short Inspection Period ({days} {unit}s)',
                        description=f'The inspection period of {days} {unit}s may be insufficient for thorough property inspection.',
                        recommendation='Negotiate for at least 7-10 days for inspection.',
                        location_ref=self._find_location(text, match.group(0)),
                        quoted_text=match.group(0),
                        confidence=0.8
                    )
                )
        
        return risks
    
    async def _generate_negotiation_points(
        self,
        risks: List[RiskFindingCreate],
        terms: Dict[str, Any],
        text: str
    ) -> List[NegotiationPointCreate]:
        """Generate negotiation points based on contract risks."""
        points = []
        
        # Price negotiation based on missing contingencies
        missing_contingencies = [r for r in risks if 'contingency' in r.title.lower()]
        if missing_contingencies:
            points.append(
                NegotiationPointCreate(
                    point_type='condition',
                    title='Missing Important Contingencies',
                    description='Contract lacks standard contingencies that protect buyers.',
                    leverage_level='high',
                    estimated_impact='Without contingencies, you risk losing deposit',
                    suggested_action='Insist on adding inspection, financing, and title contingencies before signing.'
                )
            )
        
        # As-is clause negotiation
        as_is_risks = [r for r in risks if 'As Is' in r.title]
        if as_is_risks:
            points.append(
                NegotiationPointCreate(
                    point_type='condition',
                    title='Property Sold "As Is"',
                    description='Seller wants to sell without any repairs or warranties.',
                    leverage_level='medium',
                    estimated_impact='You may need budget for unexpected repairs',
                    suggested_action='Get a thorough inspection and negotiate a credit for major issues found.'
                )
            )
        
        # Payment terms negotiation
        if not terms.get('purchase_price'):
            points.append(
                NegotiationPointCreate(
                    point_type='price',
                    title='Price Not Clearly Defined',
                    description='The purchase price is not clearly stated in the contract.',
                    leverage_level='critical',
                    estimated_impact='Cannot proceed without defined price',
                    suggested_action='Ensure exact purchase price is clearly written before signing.'
                )
            )
        
        # Timeline negotiation
        if terms.get('possession_date'):
            points.append(
                NegotiationPointCreate(
                    point_type='timeline',
                    title='Review Closing Timeline',
                    description=f'Current proposed possession date: {terms["possession_date"]}',
                    leverage_level='low',
                    estimated_impact='Timing affects moving and financing plans',
                    suggested_action='Confirm this date works with your moving schedule and financing timeline.'
                )
            )
        
        return points
    
    async def _rag_analysis(
        self,
        document_id: str,
        namespace: str
    ) -> List[RiskFindingCreate]:
        """Use RAG for deeper contract analysis."""
        risks = []
        
        try:
            queries = [
                "What are the payment terms and schedule in this agreement?",
                "Are there any unusual or unfair clauses in this contract?",
                "What contingencies protect the buyer in this agreement?",
                "What happens if either party defaults?",
                "Are there any hidden fees or costs the buyer must pay?"
            ]
            
            for query in queries:
                docs = await rag_service.similarity_search(
                    query=query,
                    namespace=namespace,
                    k=2,
                    filter={'document_id': document_id}
                )
                
                if docs:
                    result = await rag_service.analyze_with_context(
                        query=query,
                        context_docs=docs,
                        analysis_type="contract"
                    )
                    
                    # Parse response for risks (simplified)
                    if "risk" in result['response'].lower() or "issue" in result['response'].lower():
                        risks.append(
                            RiskFindingCreate(
                                category='contract',
                                severity='medium',
                                title=f'AI Analysis: {query[:50]}...',
                                description=result['response'][:200],
                                recommendation='Review this clause with a legal professional.',
                                confidence=0.6
                            )
                        )
        
        except Exception as e:
            logger.error(f"RAG analysis failed: {str(e)}")
        
        return risks
    
    def _extract_context(self, text: str, pattern: str, chars: int = 100) -> str:
        """Extract context around a pattern match."""
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return ""
        
        index = match.start()
        start = max(0, index - chars)
        end = min(len(text), match.end() + chars)
        
        return text[start:end].strip()
    
    def _find_location(self, text: str, pattern: str) -> str:
        """Find approximate location of pattern in document."""
        # Simplified - would need page tracking in production
        return "Refer to contract section containing this clause"

# Create singleton instance
contract_analyzer = ContractAnalyzer()
