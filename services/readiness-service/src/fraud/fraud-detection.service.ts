import { Injectable, Logger } from "@nestjs/common";
import type {
  BuyerCommunicationEntry,
  BuyerProfile,
  BuyerRedFlagFinding,
  BuyerRedFlagRequest,
  BuyerRedFlagResult,
  BuyerRiskLevel,
  DetectedFlag,
  FraudScanResult,
  RiskLevel,
} from "@tradeconnect/shared-types/dtos";
import { RED_FLAG_PATTERNS } from "./red-flag-patterns.js";

const SEVERITY_WEIGHTS: Record<DetectedFlag["severity"], number> = {
  LOW: 5,
  MEDIUM: 15,
  HIGH: 30,
  CRITICAL: 50,
};

const HIGH_RISK_COUNTRY_CODES = new Set([
  "AF",
  "BY",
  "CU",
  "IR",
  "KP",
  "MM",
  "RU",
  "SD",
  "SY",
  "VE",
  "YE",
  "ZW",
]);

const HIGH_RISK_COUNTRY_NAMES = new Set([
  "afghanistan",
  "belarus",
  "cuba",
  "iran",
  "north korea",
  "myanmar",
  "russia",
  "sudan",
  "syria",
  "venezuela",
  "yemen",
  "zimbabwe",
]);

const SAMPLE_KEYWORDS =
  /\b(sample|sampel|free sample|sample before contract|before contract)\b/i;
const RUSH_KEYWORDS =
  /\b(urgent|asap|immediately|today|within 24 hours|reply within|same day)\b/i;
const OFF_PLATFORM_KEYWORDS =
  /\b(outside platform|off[- ]platform|personal account|private account|bank transfer to our account|wire to our account|paypal friends and family|crypto|bitcoin|usdt)\b/i;

@Injectable()
export class FraudDetectionService {
  private readonly logger = new Logger(FraudDetectionService.name);

  scan(
    buyerId: string,
    termsText: string,
    contractText?: string,
  ): FraudScanResult {
    const fullText = [termsText, contractText].filter(Boolean).join("\n");
    const detected: DetectedFlag[] = [];

    for (const pattern of RED_FLAG_PATTERNS) {
      const match = fullText.match(pattern.regex);
      if (match?.[0]) {
        detected.push({
          id: pattern.id,
          description: pattern.description,
          severity: pattern.severity,
          category: pattern.category,
          referenceStandard: pattern.referenceStandard,
          matchedText: match[0].substring(0, 100),
        });
      }
    }

    const riskScore = this.calculateRiskScore(detected);
    const riskLevel = this.determineRiskLevel(riskScore, detected);

    this.logger.log(
      `fraud.scan buyer=${buyerId} risk=${riskLevel} score=${riskScore}`,
    );

    return {
      riskLevel,
      riskScore,
      flags: detected,
      recommendation: this.generateRecommendation(riskLevel),
    };
  }

  assessBuyerRisk(request: BuyerRedFlagRequest): BuyerRedFlagResult {
    const buyerProfile = request.buyerProfile ?? {};
    const history = request.communicationHistory ?? [];
    const flags: BuyerRedFlagFinding[] = [];
    const combinedText = history.map((entry) => entry.message).join("\n");

    const countryEvidence = this.getCountryEvidence(
      buyerProfile.countryCode,
      buyerProfile.country,
    );
    if (countryEvidence) {
      flags.push({
        id: "high_risk_country",
        description: "Buyer berasal dari yurisdiksi berisiko tinggi",
        category: "JURISDICTION",
        severity: "HIGH",
        evidence: countryEvidence,
      });
    }

    const sampleEvidence = this.getSampleEvidence(buyerProfile, combinedText);
    if (sampleEvidence) {
      flags.push({
        id: "sample_before_contract",
        description: "Buyer meminta sampel sebelum kontrak atau PO",
        category: "SAMPLE",
        severity: "MEDIUM",
        evidence: sampleEvidence,
      });
    }

    const rushEvidence = this.getRushEvidence(history);
    if (rushEvidence) {
      flags.push({
        id: "rushed_communication",
        description: "Pola komunikasi terlalu terburu-buru",
        category: "COMMUNICATION",
        severity: "MEDIUM",
        evidence: rushEvidence,
      });
    }

    const paymentEvidence = this.getOffPlatformPaymentEvidence(
      buyerProfile,
      combinedText,
    );
    if (paymentEvidence) {
      flags.push({
        id: "payment_outside_platform",
        description: "Buyer meminta pembayaran di luar platform resmi",
        category: "PAYMENT",
        severity: "HIGH",
        evidence: paymentEvidence,
      });
    }

    const riskLevel: BuyerRiskLevel = flags.some(
      (flag) => flag.severity === "HIGH",
    )
      ? "HIGH"
      : flags.length > 0
        ? "MEDIUM"
        : "LOW";

    this.logger.log(
      `buyer_risk.assess company=${buyerProfile.companyName ?? "-"} risk=${riskLevel} flags=${flags.length}`,
    );

    return {
      riskLevel,
      flags,
      recommendation: this.generateBuyerRecommendation(riskLevel),
    };
  }

  private calculateRiskScore(flags: DetectedFlag[]): number {
    const total = flags.reduce(
      (sum, f) => sum + (SEVERITY_WEIGHTS[f.severity] ?? 0),
      0,
    );
    return Math.min(100, total);
  }

  private determineRiskLevel(score: number, flags: DetectedFlag[]): RiskLevel {
    if (flags.some((f) => f.severity === "CRITICAL") || score >= 60)
      return "CRITICAL";
    if (score >= 35) return "RED";
    if (score >= 15) return "YELLOW";
    return "GREEN";
  }

  private generateRecommendation(level: RiskLevel): string {
    switch (level) {
      case "CRITICAL":
        return "HENTIKAN negosiasi segera. Laporkan ke GPEI atau LPEI untuk asesmen lebih lanjut.";
      case "RED":
        return "Jangan tanda tangani kontrak sebelum verifikasi lanjutan pembeli via INATRADE atau asosiasi ekspor.";
      case "YELLOW":
        return "Minta klarifikasi tertulis dari pembeli untuk poin-poin yang mencurigakan sebelum melanjutkan.";
      default:
        return "Tidak ditemukan red flag. Lanjutkan dengan due diligence standar.";
    }
  }

  private getCountryEvidence(
    countryCode?: string,
    countryName?: string,
  ): string | null {
    const normalizedCode = countryCode?.trim().toUpperCase();
    if (normalizedCode && HIGH_RISK_COUNTRY_CODES.has(normalizedCode)) {
      return `countryCode=${normalizedCode}`;
    }

    const trimmedName = countryName?.trim();
    const normalizedName = trimmedName?.toLowerCase();
    if (normalizedName && HIGH_RISK_COUNTRY_NAMES.has(normalizedName)) {
      return `country=${trimmedName}`;
    }

    return null;
  }

  private getSampleEvidence(
    buyerProfile: BuyerProfile,
    combinedText: string,
  ): string | null {
    if (buyerProfile.requestedSampleBeforeContract === true) {
      return "buyerProfile.requestedSampleBeforeContract=true";
    }

    const match = combinedText.match(SAMPLE_KEYWORDS);
    return match?.[0] ? `message=${match[0]}` : null;
  }

  private getRushEvidence(history: BuyerCommunicationEntry[]): string | null {
    for (const entry of history) {
      const match = entry.message.match(RUSH_KEYWORDS);
      if (match?.[0]) {
        return `message=${match[0]}`;
      }
    }

    const timestamps = history
      .map((entry) => (entry.sentAt ? Date.parse(entry.sentAt) : Number.NaN))
      .filter((value) => Number.isFinite(value));

    if (timestamps.length >= 3) {
      const spanHours =
        (Math.max(...timestamps) - Math.min(...timestamps)) / 3_600_000;
      if (spanHours <= 24) {
        return `conversation span ${spanHours.toFixed(1)}h`;
      }
    }

    return null;
  }

  private getOffPlatformPaymentEvidence(
    buyerProfile: BuyerProfile,
    combinedText: string,
  ): string | null {
    if (buyerProfile.requestedPaymentOutsidePlatform === true) {
      return "buyerProfile.requestedPaymentOutsidePlatform=true";
    }

    const match = combinedText.match(OFF_PLATFORM_KEYWORDS);
    return match?.[0] ? `message=${match[0]}` : null;
  }

  private generateBuyerRecommendation(level: BuyerRiskLevel): string {
    switch (level) {
      case "HIGH":
        return "Tunda transaksi, verifikasi identitas buyer, dan minta pembayaran melalui platform resmi atau LC/advance sebelum mengirim sampel atau barang.";
      case "MEDIUM":
        return "Minta klarifikasi tertulis dan jangan kirim sampel sebelum kontrak atau PO awal disepakati.";
      default:
        return "Tidak ada red flag utama. Lanjutkan due diligence standar.";
    }
  }
}
