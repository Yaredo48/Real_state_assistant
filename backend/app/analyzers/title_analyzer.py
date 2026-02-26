"""
Title deed analyzer for ownership and encumbrance analysis.
File: backend/app/analyzers/title_analyzer.py
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from app.services.rag_service import rag_service
from app.schemas.analysis import RiskFindingCreate, NegotiationPointCreate

logger = logging.getLogger(__name__)


class TitleAnalyzer:
    """
    Analyzer for title deeds.
    Identifies ownership issues, encumbrances, and registration problems.
    """
    
    def __init__(self):
        """Initialize title analyzer."""
        self.risk_patterns = {
            'lien': [
                r'lien',
                r'encumbrance',
                r'charge',
                r'mortgage',
                r'debt',
                r'claim'
            ],
            'ownership_dispute': [
                r'dispute',
                r'contested',
                r'litigation',
                r'court case',
                r'pending case'
            ],
            'missing_signature': [
                r'signature.*missing',
                r'unsigned',
                r'not signed'
            ],
            'expired': [
                r'expired',
                r'expiration',
                r'valid until.*\d{4}',
                r'registration.*expired'
            ],
            'forgery': [
                r'forged',
                r'fraudulent',
                r'fake',
                r'counterfeit'
            ]
        }
    
    async def analyze(
        self,
        document_id: str,
        document_text: str,
        namespace: str
    ) -> Tuple[List[RiskFindingCreate], List[NegotiationPointCreate]]:
        """
        Analyze title deed for risks.
        
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
            # Step 1: Extract key information
            info = await self._extract_title_info(document_text)
            
            # Step 2: Check for ownership issues
            ownership_risks = await self._check_ownership(info, document_text)
            risks.extend(ownership_risks)
            
            # Step 3: Check for encumbrances
            encumbrance_risks = await self._check_encumbrances(document_text)
            risks.extend(encumbrance_risks)
            
            # Step 4: Check for missing signatures/stamps
            signature_risks = await self._check_signatures(document_text)
            risks.extend(signature_risks)
            
            # Step 5: Check for expiration/validity
            expiration_risks = await self._check_expiration(document_text)
            risks.extend(expiration_risks)
            
            # Step 6: Generate negotiation points
            negotiation_points = await self._generate_negotiation_points(
                risks, info, document_text
            )
            
            # Step 7: Use RAG for deep analysis
            rag_risks = await self._rag_analysis(document_id, namespace)
            risks.extend(rag_risks)
            
        except Exception as e:
            logger.error(f"Title analysis failed: {str(e)}")
        
        return risks, negotiation_points
    
    async def _extract_title_info(self, text: str) -> Dict[str, Any]:
        """Extract key information from title deed."""
        info = {
            'owner_names': [],
            'property_description': '',
            'registration_number': '',
            'registration_date': '',
            'area': '',
            'location': ''
        }
        
        # Extract owner names (patterns like "Registered Owner: ...")
        owner_patterns = [
            r'registered owner[s]?[:\s]+([A-Za-z\s]+)',
            r'owner[s]?[:\s]+([A-Za-z\s]+)',
            r'property of[s]?[:\s]+([A-Za-z\s]+)',
            r'in the name of[s]?[:\s]+([A-Za-z\s]+)'
        ]
        
        for pattern in owner_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                info['owner_names'] = [m.strip() for m in matches]
                break
        
        # Extract registration number
        reg_patterns = [
            r'registration no[.:\s]*([A-Z0-9\-]+)',
            r'title no[.:\s]*([A-Z0-9\-]+)',
            r'deed no[.:\s]*([A-Z0-9\-]+)',
            r'certificate no[.:\s]*([A-Z0-9\-]+)'
        ]
        
        for pattern in reg_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['registration_number'] = match.group(1)
                break
        
        # Extract registration date
        date_patterns = [
            r'registration date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'dated[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['registration_date'] = match.group(1)
                break
        
        return info
    
    async def _check_ownership(
        self,
        info: Dict[str, Any],
        text: str
    ) -> List[RiskFindingCreate]:
        """Check for ownership issues."""
        risks = []
        
        # No owner found
        if not info['owner_names']:
            risks.append(
                RiskFindingCreate(
                    category='title',
                    severity='critical',
                    title='No Owner Identified',
                    description='The title deed does not clearly identify the property owner.',
                    recommendation='Request a certified copy of the title deed with clear owner information from the land registry.',
                    confidence=0.9
                )
            )
        
        # Multiple owners (possible co-ownership, but could be error)
        elif len(info['owner_names']) > 1:
            risks.append(
                RiskFindingCreate(
                    category='title',
                    severity='medium',
                    title='Multiple Owners Listed',
                    description=f'The title lists multiple owners: {", ".join(info["owner_names"])}. This may indicate co-ownership or potential inconsistency.',
                    recommendation='Verify that all listed owners are party to the sale agreement.',
                    confidence=0.7
                )
            )
        
        # Check for ownership dispute indicators
        dispute_keywords = ['dispute', 'contested', 'litigation', 'court']
        for keyword in dispute_keywords:
            if keyword in text.lower():
                risks.append(
                    RiskFindingCreate(
                        category='title',
                        severity='critical',
                        title='Ownership Dispute Indicated',
                        description=f'The document mentions "{keyword}", which may indicate an ongoing ownership dispute.',
                        recommendation='Conduct a court records search and consult with a lawyer before proceeding.',
                        confidence=0.6
                    )
                )
                break
        
        return risks
    
    async def _check_encumbrances(self, text: str) -> List[RiskFindingCreate]:
        """Check for liens and encumbrances."""
        risks = []
        
        # Check for each encumbrance type
        encumbrance_keywords = {
            'lien': ('Lien', 'A lien has been placed on this property, which must be cleared before transfer.'),
            'mortgage': ('Mortgage', 'The property has an existing mortgage that needs to be addressed.'),
            'charge': ('Charge', 'There is a charge registered against the property.'),
            'encumbrance': ('Encumbrance', 'The property has encumbrances that may affect ownership rights.'),
            'judgment': ('Judgment', 'There is a judgment against the property.'),
            'tax': ('Tax Lien', 'There may be unpaid taxes on this property.')
        }
        
        for keyword, (title, desc) in encumbrance_keywords.items():
            if keyword in text.lower():
                # Find the context around the keyword
                context = self._extract_context(text, keyword, 100)
                
                risks.append(
                    RiskFindingCreate(
                        category='title',
                        severity='high',
                        title=f'{title} Detected',
                        description=f'{desc} Context: {context}',
                        recommendation='Request a lien release or payoff statement from the current owner.',
                        location_ref=self._find_location(text, keyword),
                        quoted_text=context,
                        confidence=0.8
                    )
                )
        
        return risks
    
    async def _check_signatures(self, text: str) -> List[RiskFindingCreate]:
        """Check for missing signatures and stamps."""
        risks = []
        
        # Check for signature indicators
        signature_indicators = [
            'signature', 'signed', 'executed', 'witness'
        ]
        
        found_signatures = any(
            indicator in text.lower() for indicator in signature_indicators
        )
        
        if not found_signatures:
            risks.append(
                RiskFindingCreate(
                    category='title',
                    severity='high',
                    title='No Signatures Found',
                    description='The document appears to lack required signatures or signature indicators.',
                    recommendation='Verify that the title deed has all required signatures and official stamps.',
                    confidence=0.7
                )
            )
        
        # Check for official stamps
        stamp_indicators = [
            'stamp', 'seal', 'official', 'registered', 'certified'
        ]
        
        found_stamps = any(
            indicator in text.lower() for indicator in stamp_indicators
        )
        
        if not found_stamps:
            risks.append(
                RiskFindingCreate(
                    category='title',
                    severity='medium',
                    title='No Official Stamps Detected',
                    description='The document may lack official registration stamps or seals.',
                    recommendation='Check for physical stamps on the original document or request a certified copy.',
                    confidence=0.6
                )
            )
        
        return risks
    
    async def _check_expiration(self, text: str) -> List[RiskFindingCreate]:
        """Check for expired documents."""
        risks = []
        
        # Look for dates
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-](\d{2}|\d{4}))'
        dates = re.findall(date_pattern, text)
        
        if dates:
            # Check if any date is more than 10 years old
            current_year = datetime.now().year
            
            for date_str in dates:
                try:
                    # Parse date (simplified)
                    parts = re.split(r'[/-]', date_str[0])
                    if len(parts) == 3:
                        year = int(parts[2])
                        if year < 100:  # 2-digit year
                            year += 2000
                        
                        if current_year - year > 10:
                            risks.append(
                                RiskFindingCreate(
                                    category='title',
                                    severity='medium',
                                    title='Document May Be Outdated',
                                    description=f'The document contains a date ({date_str[0]}) that is more than 10 years old.',
                                    recommendation='Check if the title has been updated or if there are more recent registrations.',
                                    location_ref=self._find_location(text, date_str[0]),
                                    confidence=0.5
                                )
                            )
                            break
                except:
                    continue
        
        return risks
    
    async def _generate_negotiation_points(
        self,
        risks: List[RiskFindingCreate],
        info: Dict[str, Any],
        text: str
    ) -> List[NegotiationPointCreate]:
        """Generate negotiation points based on risks."""
        points = []
        
        # Price negotiation based on issues
        critical_risks = [r for r in risks if r.severity == 'critical']
        high_risks = [r for r in risks if r.severity == 'high']
        
        if critical_risks:
            points.append(
                NegotiationPointCreate(
                    point_type='price',
                    title='Significant Title Issues',
                    description=f'Found {len(critical_risks)} critical issues that may affect property value.',
                    leverage_level='high',
                    estimated_impact='Consider 10-20% price reduction or withdraw offer',
                    suggested_action='Request seller to resolve all critical issues before proceeding, or renegotiate price significantly.'
                )
            )
        elif high_risks:
            points.append(
                NegotiationPointCreate(
                    point_type='price',
                    title='Moderate Title Concerns',
                    description=f'Found {len(high_risks)} significant issues requiring attention.',
                    leverage_level='medium',
                    estimated_impact='Consider 5-10% price adjustment',
                    suggested_action='Use these findings to negotiate a better price or request seller to address issues.'
                )
            )
        
        # Encumbrance negotiation
        encumbrance_risks = [r for r in risks if 'lien' in r.title.lower() or 'mortgage' in r.title.lower()]
        if encumbrance_risks:
            points.append(
                NegotiationPointCreate(
                    point_type='condition',
                    title='Outstanding Encumbrances',
                    description='Property has existing liens or mortgages.',
                    leverage_level='high',
                    estimated_impact='Seller must clear all encumbrances before transfer',
                    suggested_action='Make offer contingent on seller clearing all liens and providing proof of release.'
                )
            )
        
        return points
    
    async def _rag_analysis(
        self,
        document_id: str,
        namespace: str
    ) -> List[RiskFindingCreate]:
        """Use RAG for deeper analysis."""
        risks = []
        
        try:
            # Query for specific title risks
            queries = [
                "What liens or encumbrances are mentioned in this title deed?",
                "Are there any ownership disputes or legal proceedings mentioned?",
                "Is this title deed properly registered and validated?",
                "Are all required signatures and stamps present?",
                "Does this title have any restrictions on transfer?"
            ]
            
            for query in queries:
                # Search for relevant chunks
                docs = await rag_service.similarity_search(
                    query=query,
                    namespace=namespace,
                    k=2,
                    filter={'document_id': document_id}
                )
                
                if docs:
                    # Analyze with LLM
                    result = await rag_service.analyze_with_context(
                        query=query,
                        context_docs=docs,
                        analysis_type="title_deed"
                    )
                    
                    # Parse response for risks
                    # This is simplified - in production, you'd parse structured output
                    if "risk" in result['response'].lower() or "issue" in result['response'].lower():
                        risks.append(
                            RiskFindingCreate(
                                category='title',
                                severity='medium',
                                title=f'AI Detected: {query[:50]}...',
                                description=result['response'][:200],
                                recommendation='Review this AI finding with a legal professional.',
                                confidence=0.6
                            )
                        )
        
        except Exception as e:
            logger.error(f"RAG analysis failed: {str(e)}")
        
        return risks
    
    def _extract_context(self, text: str, keyword: str, chars: int = 100) -> str:
        """Extract context around a keyword."""
        index = text.lower().find(keyword)
        if index == -1:
            return ""
        
        start = max(0, index - chars)
        end = min(len(text), index + len(keyword) + chars)
        
        return text[start:end].strip()
    
    def _find_location(self, text: str, keyword: str) -> str:
        """Find approximate location of keyword in document."""
        # Simplified - would need page tracking in production
        return "Refer to document section containing this text"


# Create singleton instance
title_analyzer = TitleAnalyzer()