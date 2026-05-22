import { Injectable, Logger } from '@nestjs/common';
import type {
  DetectedFlag, FraudScanResult, RiskLevel,
} from '@tradeconnect/shared-types/dtos';
import { RED_FLAG_PATTERNS } from './red-flag-patterns.js';

const SEVERITY_WEIGHTS: Record<DetectedFlag['severity'], number> = {
  LOW: 5, MEDIUM: 15, HIGH: 30, CRITICAL: 50,
};

@Injectable()
export class FraudDetectionService {
  private readonly logger = new Logger(FraudDetectionService.name);

  scan(buyerId: string, termsText: string, contractText?: string): FraudScanResult {
    const fullText = [termsText, contractText].filter(Boolean).join('\n');
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

    this.logger.log(`fraud.scan buyer=${buyerId} risk=${riskLevel} score=${riskScore}`);

    return {
      riskLevel,
      riskScore,
      flags: detected,
      recommendation: this.generateRecommendation(riskLevel),
    };
  }

  private calculateRiskScore(flags: DetectedFlag[]): number {
    const total = flags.reduce((sum, f) => sum + (SEVERITY_WEIGHTS[f.severity] ?? 0), 0);
    return Math.min(100, total);
  }

  private determineRiskLevel(score: number, flags: DetectedFlag[]): RiskLevel {
    if (flags.some((f) => f.severity === 'CRITICAL') || score >= 60) return 'CRITICAL';
    if (score >= 35) return 'RED';
    if (score >= 15) return 'YELLOW';
    return 'GREEN';
  }

  private generateRecommendation(level: RiskLevel): string {
    switch (level) {
      case 'CRITICAL':
        return 'HENTIKAN negosiasi segera. Laporkan ke GPEI atau LPEI untuk asesmen lebih lanjut.';
      case 'RED':
        return 'Jangan tanda tangani kontrak sebelum verifikasi lanjutan pembeli via INATRADE atau asosiasi ekspor.';
      case 'YELLOW':
        return 'Minta klarifikasi tertulis dari pembeli untuk poin-poin yang mencurigakan sebelum melanjutkan.';
      default:
        return 'Tidak ditemukan red flag. Lanjutkan dengan due diligence standar.';
    }
  }
}