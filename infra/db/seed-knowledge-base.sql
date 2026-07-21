-- ============================================================
-- TradeConnect — Export Knowledge Base Seed Data
-- Loaded by: psql -f infra/db/seed-knowledge-base.sql
-- Or via: docker exec -i postgres psql -U tc_user -d tradeconnect < infra/db/seed-knowledge-base.sql
--
-- Categories: incoterms | payment_terms | documents | regulations | negotiation | logistics | market_intelligence
-- ============================================================

INSERT INTO export_knowledge_base (title, content, category, source) VALUES

-- ══════════════════════════════════════════════════════════════
-- INCOTERMS 2020
-- ══════════════════════════════════════════════════════════════

('Incoterms 2020 Overview',
'Incoterms (International Commercial Terms) 2020 are standardized trade terms published by the International Chamber of Commerce (ICC). They define the responsibilities of buyers and sellers in international trade transactions, covering delivery, risk transfer, and cost allocation.

Key Incoterms for Indonesian UMKM exporters:

EXW (Ex Works): Seller''s minimum obligation. Buyer collects goods at seller''s premises and bears all costs and risks from that point. Not recommended for inexperienced exporters as buyer handles all Indonesian export formalities.

FOB (Free On Board): Seller delivers goods on board the vessel at the named port of shipment (e.g., FOB Tanjung Priok). Risk transfers when goods are on board. Seller handles Indonesian export clearance. Most common term for Indonesian SME exports.

CIF (Cost, Insurance, Freight): Seller pays freight and insurance to destination port. Risk still transfers when goods are loaded on vessel. Seller arranges and pays for ocean freight and minimum insurance. Buyer handles import clearance at destination.

CFR (Cost and Freight): Like CIF but buyer arranges insurance. Seller pays freight to named destination port.

DAP (Delivered at Place): Seller delivers goods to named destination, ready for unloading. Buyer handles import duties and clearance. Higher seller obligation than FOB/CIF.

DDP (Delivered Duty Paid): Seller''s maximum obligation — delivers to buyer''s premises with all duties paid. Requires seller to handle import formalities in buyer''s country. Complex for UMKM.

Recommendation for UMKM: Use FOB for buyers who prefer to arrange their own freight, or CIF when the buyer requests it. Avoid DDP unless you have a logistics partner in the buyer''s country.',
'incoterms',
'ICC Incoterms 2020'),

('FOB vs CIF — Which to Choose',
'Choosing between FOB and CIF depends on your capabilities and the buyer''s preference.

FOB (Free On Board):
- Price quoted at port of loading (e.g., FOB Tanjung Priok, FOB Belawan)
- Buyer arranges and pays ocean freight + insurance
- Lower quote price, but buyer has full freight control
- Use when: buyer has preferred shipping lines or freight forwarders
- Risk for seller: limited (ends when goods cross ship''s rail)

CIF (Cost, Insurance, and Freight):
- Price includes ocean freight and minimum cargo insurance to destination port
- Seller controls freight routing — use preferred forwarder for better rates
- Higher quoted unit price, but buyer sees all-in cost
- Use when: you have competitive freight rates or buyer requests CIF
- Risk for seller: higher (arranges freight, but risk still transfers at origin port)

Price Calculation:
CIF Price = FOB Price + Ocean Freight per unit + Insurance (typically 110% of CIF × 0.3%)

Example: FOB Tanjung Priok $5.00/kg for coffee to Hamburg
Ocean freight: $0.25/kg → CFR = $5.25/kg
Insurance: $5.25 × 1.10 × 0.003 ≈ $0.017/kg → CIF = $5.267/kg ≈ $5.27/kg

Always specify the full Incoterm: "FOB Tanjung Priok, Indonesia" not just "FOB".',
'incoterms',
'ICC Incoterms 2020 / TradeConnect Advisory'),

-- ══════════════════════════════════════════════════════════════
-- PAYMENT TERMS
-- ══════════════════════════════════════════════════════════════

('Payment Terms Guide for Indonesian Exporters',
'Understanding international payment methods is critical for UMKM exporters to protect against non-payment risk.

1. LETTER OF CREDIT (LC / L/C)
Safest payment method for exporters. A bank in the buyer''s country issues a guarantee of payment subject to presentation of compliant shipping documents.

Types:
- LC at Sight: Payment made immediately upon presentation of compliant documents
- LC 30/60/90 days: Payment deferred after document acceptance (usance LC)
- Irrevocable LC: Cannot be cancelled without exporter''s consent — always request this

Key documents required for LC:
- Commercial Invoice (matching LC terms exactly)
- Bill of Lading (clean on-board)
- Packing List
- Certificate of Origin (Form D for ASEAN, Form E for China, etc.)
- Insurance Certificate (for CIF terms)
- Any special certificates (phytosanitary, halal, organic)

UMKM recommendation: Always request irrevocable, confirmed LC at sight for new buyers.

2. TELEGRAPHIC TRANSFER (TT / Wire Transfer)
Direct bank transfer. Faster but riskier than LC.

Common structures:
- TT 100% advance: Full payment before shipment. Lowest risk for seller, highest for buyer.
- TT 30% advance + 70% against BL copy: 30% deposit, balance paid when B/L scan sent. Common compromise.
- TT 30/70 against original documents: Balance paid against courier of original docs.
- TT net 30/60: Full payment within 30/60 days of B/L date. High risk — avoid with new buyers.

3. CASH AGAINST DOCUMENTS (CAD / D/P)
Seller ships goods and sends documents through seller''s bank to buyer''s bank. Buyer pays to release documents. Lower cost than LC but no bank guarantee of payment.

4. OPEN ACCOUNT
Goods shipped before payment. Highest risk for seller. Only use with long-term trusted buyers and consider trade credit insurance.',
'payment_terms',
'Bank Indonesia Export Finance Guide / TradeConnect'),

('Negotiating Payment Terms with New Buyers',
'When approaching payment terms negotiation with new international buyers:

OPENING POSITION: Always open with the safest term (LC at sight or TT 100% advance). This anchors the negotiation high and gives room to concede.

COMMON BUYER PUSHBACKS AND RESPONSES:

Buyer: "We don''t do LC, too expensive."
Response: "We understand LC fees are a cost. As an alternative, we can offer TT with 30% deposit and 70% against copy of Bill of Lading. This protects both sides — you see the shipment before paying the balance."

Buyer: "Can we do open account / net 30?"
Response: "We work with established payment terms for new partnerships. Once we complete 2-3 successful shipments, we would be happy to discuss extended terms. For now, TT 30/70 is our standard for first orders."

Buyer: "Our company policy is TT net 60."
Response: "We appreciate your standard process. For the first shipment, we propose TT 30% advance + 70% at 30 days from B/L date. We can discuss extending to 45-60 days after our relationship is established."

NEVER agree to:
- Net 60+ terms with a new buyer
- Open account without trade credit insurance
- Changing LC payment terms mid-negotiation under pressure

Always get payment term agreement in writing (email confirmation minimum) before proceeding to production.',
'payment_terms',
'TradeConnect Negotiation Playbook'),

-- ══════════════════════════════════════════════════════════════
-- EXPORT DOCUMENTS
-- ══════════════════════════════════════════════════════════════

('Required Export Documents for Indonesian Agricultural Products',
'Indonesian UMKM exporters of agricultural products (coffee, spices, cocoa, palm oil derivatives, seafood) must prepare these documents:

MANDATORY DOCUMENTS:

1. Commercial Invoice
- Must match LC terms exactly (if LC payment)
- Include: seller and buyer details, HS code, description, quantity, unit price, total value, Incoterm, payment terms
- Date cannot be before LC issuance date

2. Packing List
- Detailed breakdown of cartons/bags/containers
- Net weight, gross weight, dimensions, number of packages
- Must reconcile with invoice quantities

3. Bill of Lading (B/L) or Airway Bill (AWB)
- Issued by shipping line
- "Clean on board" required for LC
- Consignee: buyer (or "to order" for negotiable B/L)
- Notify party: buyer or buyer''s agent

4. Certificate of Origin (COO)
- Form SKA issued by Indonesian Chamber of Commerce (KADIN) or Ministry of Trade
- Preferential COOs for FTA benefits: Form D (ASEAN), Form E (China-ASEAN ACFTA), Form AI (India), Form JIEPA (Japan), Form AK (Korea), Form AZ (Australia/NZ)
- Non-preferential: Certificate of Indonesian Origin (CIO)

PRODUCT-SPECIFIC DOCUMENTS:

Agricultural / Food Products:
- Phytosanitary Certificate — issued by Ministry of Agriculture (Badan Karantina)
- Health Certificate — for processed food products
- BPOM registration number — for packaged consumer food
- SNI certificate if required

Halal Products:
- Halal Certificate issued by MUI (Majelis Ulama Indonesia)
- Required for buyers in Muslim-majority markets (Middle East, Malaysia, etc.)

Organic Products:
- Organic certification (Lembaga Sertifikasi Organik Seloliman / Inofice / Control Union)
- Required for premium organic market positioning

Coffee Specifically:
- ICO (International Coffee Organization) Certificate of Origin for ICO member importing countries
- Cup quality test report (Q grader) for specialty grades

PROCESSING TIME: Allow 5-10 business days to obtain all certificates before shipment date.',
'documents',
'Kemendag / Badan Karantina / KADIN Indonesia'),

('Certificate of Origin — How to Apply',
'Certificate of Origin (COO / Surat Keterangan Asal) is required for most international shipments to claim preferential tariff rates under Indonesia''s free trade agreements.

APPLICATION PROCESS (INATRADE System):
1. Register at inatrade.kemendag.go.id
2. Prepare: Commercial Invoice, Packing List, draft B/L, product specification
3. Submit COO application online (select correct form: D, E, AI, etc.)
4. Pay administrative fee (varies by form type, typically IDR 50,000-200,000)
5. Inspection visit may be required for first-time applicants
6. COO issued within 1-3 working days (online) or same day (walk-in at regional Disperindag)

PREFERENTIAL TARIFF BENEFITS (examples):
- Form D (ASEAN): 0% tariff in ASEAN countries for eligible products
- Form E (ACFTA): Reduced tariffs to China (many agricultural products 0%)
- Form AI (AIFTA): Reduced tariffs to India
- Form JIEPA: Preferential rates to Japan

IMPORTANT: The HS code on the COO must match the Commercial Invoice and B/L exactly. Mismatch will cause customs clearance delays and potential penalty at destination.',
'documents',
'Kemendag INATRADE Portal / TradeConnect'),

-- ══════════════════════════════════════════════════════════════
-- REGULATIONS
-- ══════════════════════════════════════════════════════════════

('Indonesian Export Licensing Requirements',
'Not all products can be exported freely from Indonesia. Understanding export licensing requirements prevents delays and penalties.

PRODUCTS REQUIRING EXPORT LICENSE (Izin Ekspor):

1. Regulated Export Products (Barang Diatur Ekspor):
- Raw rattan, rattan furniture (requires value-added proof)
- Raw/semi-processed forest products
- Protected wildlife and plant species (CITES permits)
- Certain chemical precursors

2. Monitored Export Products (Barang Diawasi Ekspor):
- Coffee (must be registered as coffee exporter with Ditjen Daglu)
- Cocoa beans (must meet grading standards per SNI)
- Palm oil and derivatives (follows export levy/duty schedule)
- Crude rubber

3. Export Prohibited Products (Barang Dilarang Ekspor):
- Sand and sea sand
- Raw ore (certain minerals, before processing)
- Certain protected animal species

COFFEE EXPORT REGISTRATION:
Indonesian coffee exporters must register with Directorate General of Foreign Trade (Ditjen Daglu) as an Eksportir Terdaftar Kopi (ETK). Registration requires:
- NIB (Nomor Induk Berusaha) via OSS system
- Proof of production capacity or trading license
- SKDP (Surat Keterangan Domisili Perusahaan)

EXPORT DUTY (Bea Keluar):
Some products carry export duties. Check current rates at DJBC (customs.go.id):
- CPO (crude palm oil): varies with price formula
- Leather (raw): regulated

Always verify current regulations at kemendag.go.id or inatrade.kemendag.go.id before shipping.',
'regulations',
'Kemendag / Ditjen Daglu / DJBC Indonesia'),

('Sanitary and Phytosanitary (SPS) Requirements for Food Exports',
'International buyers of Indonesian food products (coffee, spices, cocoa, seafood, processed foods) increasingly require compliance with importing country SPS standards.

EU MARKET REQUIREMENTS:
- EU Food Safety Regulations (EC 178/2002, EC 852/2004)
- Maximum Residue Levels (MRL) for pesticides — check EFSA database
- Aflatoxin limits: B1 ≤ 5 μg/kg for coffee, total aflatoxins ≤ 10 μg/kg
- Ochratoxin A: ≤ 10 μg/kg for roasted coffee (Regulation EC 1881/2006)
- EU Organic: products sold as organic in EU must be certified by EU-recognized body

USA MARKET:
- FDA registration required for food facilities (can register as foreign supplier)
- FDA FSMA (Food Safety Modernization Act) — Foreign Supplier Verification Program
- USDA National Organic Program (NOP) for organic claims

JAPAN MARKET:
- JAS (Japanese Agricultural Standard) for organic labeling
- Positive list system for agricultural chemicals — very strict

HALAL MARKETS (Middle East, Malaysia):
- MUI halal certification recognized in Malaysia, GCC countries
- UAE: Emirates Authority for Standardization certification
- Malaysia: JAKIM recognized MUI/LPPOM

KEY CERTIFICATE FOR COFFEE/SPICES:
Indonesian Spice and Coffee Council grading certificates, SNI compliance, and cup quality reports (for specialty coffee) are increasingly required by premium buyers.',
'regulations',
'Kemendag / Badan Karantina / BPOM / EU RASFF Database'),

-- ══════════════════════════════════════════════════════════════
-- NEGOTIATION TEMPLATES
-- ══════════════════════════════════════════════════════════════

('RFQ Response Email Template',
'Template for responding to a Request for Quotation from an international buyer.

---
Subject: Re: [Buyer''s Subject] — Quotation for [Product Name]

Dear [Buyer Name / Title],

Thank you for your inquiry regarding [Product Name]. We are pleased to provide the following quotation.

PRODUCT SPECIFICATION:
- Product: [Full product name and grade]
- HS Code: [HS Code]
- Origin: [City/Province], Indonesia
- Processing: [Natural / Washed / Semi-washed / Honey]
- Certifications: [Organic / Halal / Fair Trade / UTZ etc.]
- Moisture Content: [X%] max
- Defects: [Grade specification]

PRICING (valid 14 days from today):
- Unit Price: USD [PRICE] per kg, [FOB/CIF] [Port Name]
- Minimum Order Quantity (MOQ): [X] kg per shipment
- Payment Terms: [LC at sight / TT 30%+70% against BL copy]

LOGISTICS:
- Packaging: [25kg jute bags / 60kg GrainPro bags / etc.]
- Lead Time: [X] working days after receipt of confirmed LC / payment
- Port of Loading: [Tanjung Priok / Belawan / Tanjung Perak]
- Estimated Transit Time: [X] days to [destination port]

DOCUMENTS PROVIDED:
Commercial Invoice, Packing List, Bill of Lading, Certificate of Origin ([Form D/E/etc.] for [Incoterm benefits]), Phytosanitary Certificate, [other applicable certificates]

We would be happy to send samples upon request (shipping cost at buyer''s expense).

Please do not hesitate to contact us for any clarification.

Best regards,
[Name]
[Title]
[Company Name]
[Email] | [Phone] | [WhatsApp]
---',
'negotiation',
'TradeConnect Email Templates'),

('Price Negotiation Response Template',
'Template for responding when a buyer requests a price reduction.

---
Dear [Buyer Name],

Thank you for your continued interest in [Product Name] and for sharing your price expectations.

We appreciate your transparency. Allow us to provide some context:

Our pricing reflects the [specialty grade / single origin / certified organic / fair trade premium] nature of our product. [Product Name] from [Region] is [brief quality differentiator — e.g., "recognized for its distinct chocolate and citrus notes, scoring 85+ on the SCA cupping scale"]. The pricing also accounts for [certifications / sustainable farming practices / quality control procedures].

Regarding your target price of USD [Buyer''s Offer]:

After careful review, we are able to offer the following volume-based pricing:
- [MOQ] – [X] kg: USD [Price A] / kg [Incoterm]
- [X+1] – [Y] kg: USD [Price B] / kg [Incoterm]
- Above [Y] kg: USD [Price C] / kg [Incoterm] (subject to discussion)

We believe this structure rewards your commitment to volume while ensuring product quality is not compromised.

As an alternative, we could explore:
1. Adjusting packaging to reduce per-unit cost (e.g., bulk 60kg bags vs. retail 1kg packs)
2. A trial shipment at standard price to establish quality confidence before scaling
3. Flexible payment terms for larger, consistent orders

We are committed to a long-term partnership and look forward to finding an arrangement that works for both sides.

Could we schedule a brief call to discuss further?

Best regards,
[Name]
[Company]
---',
'negotiation',
'TradeConnect Negotiation Playbook'),

('Complaint Handling Email Template',
'Template for professionally responding to quality or delivery complaints.

---
Dear [Buyer Name],

Thank you for bringing this matter to our attention. We sincerely apologize for the inconvenience you have experienced regarding your shipment [Invoice/BL Number] dated [Date].

We take quality and delivery reliability very seriously, and we want to resolve this matter promptly.

To investigate your complaint effectively, we kindly request the following documentation:
1. Photos or video of the goods showing the issue
2. Independent inspection report (if available)
3. Packing list comparison showing discrepancy (for short shipment claims)
4. Moisture / quality test results from an accredited lab (for quality claims)

Upon receipt of the above, we commit to providing our response within [5] working days.

Preliminary assessment:
Based on your description, we believe this may be related to [possible cause — e.g., "moisture absorption during transit" / "packaging damage in transit"]. We will cross-reference with our Quality Control records and shipping documentation.

Our standard process for verified claims:
- Quality defect confirmed within our responsibility: replacement in next shipment or credit note
- Damage in transit: we will assist in filing insurance claim on CIF terms / advise on carrier claim on FOB terms
- Quantity discrepancy: weight certificate from loading port will be provided as reference

We value our business relationship and are committed to reaching a fair resolution. Please share the supporting documents at your earliest convenience.

Best regards,
[Name]
[Quality / Operations Manager]
[Company]
---',
'negotiation',
'TradeConnect Email Templates'),

-- ══════════════════════════════════════════════════════════════
-- LOGISTICS
-- ══════════════════════════════════════════════════════════════

('Indonesian Export Logistics Overview',
'Key logistics information for UMKM exporters shipping from Indonesia.

MAJOR PORTS OF EXPORT:
- Tanjung Priok (Jakarta): Largest container port. Direct services to Europe, USA, Asia. Best option for most exporters.
- Tanjung Perak (Surabaya): Second largest. Good for East Java and Eastern Indonesia products.
- Belawan (Medan): Best for North Sumatra products (Gayo coffee, palm oil, rubber).
- Teluk Bayur (Padang): West Sumatra products.
- Makassar: Eastern Indonesia and Sulawesi products (cocoa).

FREIGHT FORWARDERS (Ekspedisi Muatan Kapal Laut / EMKL):
- Reputable Indonesian freight forwarders: PT Samudera Indonesia, PT ICTSI, Panasea Indotrans
- Use a licensed EMKL with IATA/FIATA membership for air freight
- Get at least 3 freight quotes before committing to a forwarder

CONTAINER TYPES FOR AGRICULTURAL PRODUCTS:
- Dry container (20ft / 40ft): Coffee, dried spices, handicrafts, processed food (sealed packaging)
- Reefer container: Fresh/frozen seafood, temperature-sensitive products
- Less-than-Container Load (LCL / FCL): LCL for shipments under ~12 CBM; FCL for larger volumes (cost-effective at full container)

ESTIMATED TRANSIT TIMES FROM TANJUNG PRIOK:
- Singapore: 2-3 days (transshipment hub)
- China: 5-10 days
- Japan/Korea: 10-14 days
- Europe (Hamburg, Rotterdam): 22-30 days
- USA (LA, New York): 18-25 days
- Middle East: 12-18 days

INSURANCE:
- Cargo insurance: recommended for all shipments, typically 110% of CIF value × 0.3-0.5%
- Indonesian insurers: Asuransi Jasindo, Asuransi Wahana Tata
- Open cover policy: cost-effective for regular exporters',
'logistics',
'Kemenhub / INSA / TradeConnect'),

('Customs Export Procedure (PEB — Pemberitahuan Ekspor Barang)',
'Step-by-step guide to Indonesian customs export declaration (PEB / Pemberitahuan Ekspor Barang).

PARTIES INVOLVED:
- Eksportir (Exporter): your company
- PPJK (Customs Agent / Freight Forwarder): handles PEB filing on your behalf
- DJBC (Bea Cukai): Indonesian Customs — Direktorat Jenderal Bea dan Cukai

PEB FILING STEPS:
1. Prepare export documents: Commercial Invoice, Packing List, any required licenses
2. Engage a licensed PPJK (customs broker/freight forwarder)
3. PPJK inputs PEB data into DJBC online system (BC 3.0 / portal.beacukai.go.id)
4. PEB submitted minimum 24 hours before vessel departure
5. DJBC reviews: may approve directly (SPPB — green channel) or request inspection (red channel)
6. After approval: load goods onto vessel
7. After goods on board: PPJK obtains laden B/L from shipping line

DOCUMENTS SUBMITTED TO CUSTOMS:
- PEB (export declaration form)
- Commercial Invoice
- Packing List
- Export license (if applicable for regulated goods)
- Supporting certificates as required

EXPORT DUTIES:
Certain products (palm oil, leather, cocoa beans) carry export duties (Bea Keluar). PPJK will calculate and pay these on exporter''s behalf — reimbursed to PPJK.

NETT EXPORT PROCEEDS REPATRIATION (DHE):
Indonesian regulation (GR 36/2023) requires exporters of natural resources (mining, plantation, forestry, fisheries) to repatriate export proceeds to Indonesian banks:
- Plantation products (coffee, CPO): proceeds must be received in Indonesian bank within 3 months of B/L date
- Consult your bank for DHE reporting requirements',
'logistics',
'DJBC (Indonesian Customs) / Bank Indonesia'),

-- ══════════════════════════════════════════════════════════════
-- MARKET INTELLIGENCE
-- ══════════════════════════════════════════════════════════════

('Key Export Markets for Indonesian UMKM Products',
'Overview of priority export markets for common Indonesian UMKM export products.

COFFEE (HS 0901):
Top importers of Indonesian coffee: USA, Japan, Germany, Malaysia, Italy
- Specialty coffee demand: USA, Japan, Australia, Netherlands — premium pricing for single-origin traceable coffee
- Commercial grade: Malaysia, Singapore, domestic roasters
- Gayo (Aceh), Toraja, Flores, Sumatra Mandheling are premium origins with global recognition
- Organic/Fair Trade premium: 15-30% above conventional price
- Market trend: Cold brew ready beans, natural process specialty, growing direct-trade relationships

HANDICRAFTS / RATTAN / BAMBOO (HS 4601, 9403):
Top markets: USA, Netherlands, Germany, Japan, Australia
- USA: Home décor, wellness accessories, sustainable lifestyle products
- EU: Eco-friendly labeling important, EUDR compliance for rattan
- Japan: High-quality craftsmanship standards, precise specifications required

SPICES (HS 0904-0910):
- Nutmeg/Mace (Indonesia = 75% world supply): Netherlands, USA, India
- Black/White Pepper: Vietnam (processing), USA, Germany
- Cloves: India, Pakistan, Sri Lanka
- Cinnamon: USA (prefer Cassia), EU, Middle East

COCOA (HS 1801):
- Indonesian cocoa beans: USA, Malaysia (processing), EU
- Value-added: cocoa butter, cocoa powder, chocolate couverture — higher margins
- EU Deforestation Regulation (EUDR) from Dec 2024: requires traceability documentation

SEAFOOD (HS 0306, 0302):
- Shrimp: USA, Japan, EU — largest importers
- Tuna: Japan (sashimi grade), EU, USA
- Certification: ASC, MSC increasingly required by European and US buyers

ESSENTIAL OILS / COSMETICS (HS 3301, 3302, 3304):
- Vetiver, Patchouli, Ylang-ylang, Clove leaf oil: France (fragrance), USA, Germany
- Natural cosmetics ingredients: EU, USA premium market
- IFRA compliance important for fragrance applications',
'market_intelligence',
'ITC (International Trade Centre) / BPS / Kemendag'),

('Price Benchmarking — Indonesian Export Products 2025',
'Reference price ranges for common Indonesian export commodities. Use for anchoring, not for exact quotation.

SPECIALTY COFFEE (FOB Tanjung Priok / Belawan):
- Gayo Arabika Grade 1 (Q Grade 85+): USD 4.50–6.50/kg
- Gayo Arabika Grade 1 (Q Grade 80-84): USD 3.50–4.50/kg
- Toraja Arabika Grade 1: USD 4.00–5.50/kg
- Flores Bajawa Arabika: USD 3.80–5.00/kg
- Robusta Grade 1 (Lampung): USD 1.80–2.50/kg
- Natural/Honey Process premium: +USD 0.50–1.50/kg above washed price

COCOA BEANS:
- Indonesian fermented cocoa (bulk): USD 2.80–3.50/kg (follows ICCO futures)
- Sulawesi fine flavour cocoa: USD 3.50–4.50/kg

SPICES:
- Black pepper (500-550 g/L density): USD 4.00–5.50/kg FOB
- White pepper (Muntok): USD 6.00–8.00/kg FOB
- Nutmeg (A/B/C grade): USD 4.00–7.00/kg
- Cloves (whole, Grade A): USD 7.00–10.00/kg

HANDICRAFTS:
- Rattan furniture (outdoor dining set): USD 150–400/set FOB
- Bamboo baskets (craft grade): USD 2–15/piece
- Wooden furniture (teak): USD 200–800/piece

NOTE: These are indicative benchmark ranges only. Actual pricing depends on:
- Current commodity futures (for coffee, cocoa, pepper)
- Grade, processing method, certifications
- Volume of order (larger = lower per-unit price)
- Market conditions and buyer destination
- Currency fluctuations (IDR/USD)

Always anchor your opening offer at the upper end of market range and justify with quality differentiators.',
'market_intelligence',
'ITC Market Price Information System / Kemendag SIPK 2025')

ON CONFLICT DO NOTHING;
