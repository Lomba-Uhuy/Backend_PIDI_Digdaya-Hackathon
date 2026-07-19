import { describe, expect, it } from "vitest";
import { FraudDetectionService } from "./fraud-detection.service.js";

describe("FraudDetectionService", () => {
  const svc = new FraudDetectionService();

  it("returns GREEN for clean text", () => {
    const r = svc.scan(
      "buyer-x",
      "We would like to order 500 units, paid via LC at sight.",
    );
    expect(r.riskLevel).toBe("GREEN");
    expect(r.flags).toHaveLength(0);
  });

  it("flags OFFSHORE_PAYMENT as CRITICAL", () => {
    const r = svc.scan(
      "buyer-x",
      "Please send invoice but route payment to our offshore account in Mauritius.",
    );
    expect(r.flags.some((f) => f.id === "OFFSHORE_PAYMENT")).toBe(true);
    expect(r.riskLevel).toBe("CRITICAL");
  });

  it("flags INVOICE_MANIPULATION as CRITICAL", () => {
    const r = svc.scan(
      "buyer-x",
      "Can you under-invoice the shipment to reduce customs on our side?",
    );
    expect(r.flags.some((f) => f.id === "INVOICE_MANIPULATION")).toBe(true);
    expect(r.riskLevel).toBe("CRITICAL");
  });

  it("raises HIGH risk for off-platform payment or high-risk country", () => {
    const r = svc.assessBuyerRisk({
      buyerProfile: {
        companyName: "Shady Import Co",
        countryCode: "IR",
        requestedPaymentOutsidePlatform: true,
      },
      communicationHistory: [
        {
          sender: "buyer",
          message:
            "Please transfer to our personal account outside the platform.",
          sentAt: "2026-05-29T10:00:00Z",
          channel: "email",
        },
      ],
    });

    expect(r.riskLevel).toBe("HIGH");
    expect(r.flags.some((f) => f.id === "high_risk_country")).toBe(true);
    expect(r.flags.some((f) => f.id === "payment_outside_platform")).toBe(true);
  });

  it("returns MEDIUM for sample-before-contract and rushed communication", () => {
    const r = svc.assessBuyerRisk({
      buyerProfile: {
        companyName: "New Buyer GmbH",
        country: "Germany",
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
          message: "This is urgent. Reply within 24 hours.",
          sentAt: "2026-05-29T12:00:00Z",
          channel: "email",
        },
        {
          sender: "buyer",
          message: "We need to move fast today.",
          sentAt: "2026-05-29T16:00:00Z",
          channel: "email",
        },
      ],
    });

    expect(r.riskLevel).toBe("MEDIUM");
    expect(r.flags.some((f) => f.id === "sample_before_contract")).toBe(true);
    expect(r.flags.some((f) => f.id === "rushed_communication")).toBe(true);
  });
});
