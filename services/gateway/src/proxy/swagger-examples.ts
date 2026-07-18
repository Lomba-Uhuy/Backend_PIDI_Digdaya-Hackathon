// ── Request body examples for @ApiBody ───────────────────────────────────────
// Response schemas are defined by typed DTO classes in dto/*-response.dto.ts

// Auth
export const authRegisterExample = {
  email: "owner@kopigayo.id",
  password: "KopiGayo!2026",
};

export const authLoginExample = {
  email: "owner@kopigayo.id",
  password: "KopiGayo!2026",
};

// UMKM & Products
export const createUmkmExample = {
  legalName: "CV Kopi Gayo Nusantara",
  nib: "1234567890123",
  description: "Produsen kopi arabika specialty dari Takengon, Aceh Tengah.",
};

export const createProductExample = {
  name: "Kopi Arabika Gayo Grade A",
  description:
    "Kopi arabika specialty dari Aceh Tengah, proses semi-washed, cocok untuk pasar roastery premium.",
  moq: 50,
  monthlyCapacity: 10000,
  priceMin: 5.5,
  priceMax: 6.5,
  hpp: 3.5,
  photoUrls: [
    "https://storage.tradeconnect.id/products/gayo-grade-a-1.jpg",
    "https://storage.tradeconnect.id/products/gayo-grade-a-2.jpg",
  ],
};

// Matching
export const matchingSearchExample = {
  product_id: "5d9f2d9e-0f0f-4cb0-9d84-1d7a9ef5d8d7",
  top_k: 5,
  country_filter: ["DE", "NL", "JP"],
};

export const matchBuyersExample = {
  embedding: [0.0123, -0.0456, 0.0789, "... (1024 floats total)"],
  top_k: 10,
  country_filter: ["DE", "NL", "JP"],
  min_volume: 100,
  category: "09",
};

export const hsClassifyExample = {
  description:
    "Kopi arabika roasted whole bean dari Gayo Aceh. Specialty grade, fermentasi 72 jam, dried natural.",
  top_k: 3,
};

// Comms
export const negotiationDraftExample = {
  inquiry_text:
    "Kami tertarik dengan kopi Gayo Anda. Bisakah Anda memberikan quotation untuk 500kg kopi roasted whole bean?",
  product_id: "5d9f2d9e-0f0f-4cb0-9d84-1d7a9ef5d8d7",
  buyer_id: "2c2d2c1b-5a7d-4d25-8bc3-e0bf7f2f2d11",
};

export const generateReplyExample = {
  importer_email:
    "Dear Sir/Madam, We are a specialty coffee importer based in Hamburg. We are interested in your Gayo Arabika Grade 1. Could you please provide a proforma invoice for 500kg, FOB Belawan? We would prefer LC at sight payment terms.",
  product_id: "5d9f2d9e-0f0f-4cb0-9d84-1d7a9ef5d8d7",
  buyer_id: "2c2d2c1b-5a7d-4d25-8bc3-e0bf7f2f2d11",
};

export const intentExample = {
  email_text:
    "We are interested in your coffee products. Could you provide a quotation for 500kg? We prefer LC at sight payment terms.",
};

// Readiness
export const pricingExample = {
  hpp: 3.5,
  originCharges: 0.5,
  qty: 500,
  oceanFreight: 0.3,
  insuranceAmount: 4.4,
  exportDuty: 0.1,
  profitMarginPct: 20,
  hsCode: "0901",
  exchangeRate: 16000,
};

export const fraudScanExample = {
  buyerId: "2c2d2c1b-5a7d-4d25-8bc3-e0bf7f2f2d11",
  termsText:
    "Payment must be made in full by wire transfer. Please ignore the invoice if the amount is overpaid.",
  contractText:
    "Goods will be shipped to a third-party warehouse before bank clearance is completed.",
};

export const checkRedFlagExample = {
  buyerProfile: {
    companyName: "PT Global Trading Asia",
    countryCode: "AE",
    requestedSampleBeforeContract: true,
    requestedPaymentOutsidePlatform: false,
  },
  communicationHistory: [
    {
      sender: "buyer",
      message: "Please send sample first before we finalize the contract.",
      sentAt: "2026-05-29T10:00:00Z",
      channel: "email",
    },
    {
      sender: "buyer",
      message: "This is urgent. Please reply within 24 hours.",
      sentAt: "2026-05-29T12:00:00Z",
      channel: "email",
    },
  ],
};

export const verifyNibExample = {
  nib: "1234567890",
};
