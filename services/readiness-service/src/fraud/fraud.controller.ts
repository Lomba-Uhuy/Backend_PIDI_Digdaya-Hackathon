import { Body, Controller, Post } from "@nestjs/common";
import {
  ApiBody,
  ApiOkResponse,
  ApiOperation,
  ApiProperty,
  ApiPropertyOptional,
  ApiTags,
} from "@nestjs/swagger";
import {
  IsOptional,
  IsString,
  IsUUID,
  MaxLength,
  MinLength,
} from "class-validator";
import { FraudDetectionService } from "./fraud-detection.service.js";
import {
  CheckRedFlagDto,
  CheckRedFlagResponseDto,
} from "./dto/check-red-flag.dto.js";

class FraudScanDto {
  @ApiProperty({ example: "2c2d2c1b-5a7d-4d25-8bc3-e0bf7f2f2d11" })
  @IsUUID()
  buyerId!: string;

  @ApiProperty({
    example:
      "Payment must be made in full by wire transfer. Please ignore the invoice if the amount is overpaid.",
  })
  @IsString()
  @MinLength(1)
  @MaxLength(20_000)
  termsText!: string;

  @ApiPropertyOptional({
    example:
      "Goods will be shipped to a third-party warehouse before bank clearance is completed.",
  })
  @IsString()
  @MaxLength(50_000)
  @IsOptional()
  contractText?: string;
}

const fraudScanExample = {
  buyerId: "2c2d2c1b-5a7d-4d25-8bc3-e0bf7f2f2d11",
  termsText:
    "Payment must be made in full by wire transfer. Please ignore the invoice if the amount is overpaid.",
  contractText:
    "Goods will be shipped to a third-party warehouse before bank clearance is completed.",
};

const fraudScanResponseExample = {
  riskLevel: "RED",
  riskScore: 45,
  flags: [
    {
      id: "overpayment_scam",
      description: "Permintaan kelebihan bayar yang harus dikembalikan.",
      severity: "HIGH",
      category: "PAYMENT",
      referenceStandard: "ICC red flag catalogue",
      matchedText: "overpaid",
    },
  ],
  recommendation:
    "Jangan tanda tangani kontrak sebelum verifikasi lanjutan pembeli via INATRADE atau asosiasi ekspor.",
};

const checkRedFlagExample = {
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

const checkRedFlagResponseExample = {
  riskLevel: "HIGH",
  flags: [
    {
      id: "sample_before_contract",
      description: "Buyer meminta sampel sebelum kontrak atau PO",
      category: "SAMPLE",
      severity: "MEDIUM",
      evidence:
        "message=Please send sample first before we finalize the contract.",
    },
    {
      id: "rushed_communication",
      description: "Pola komunikasi terlalu terburu-buru",
      category: "COMMUNICATION",
      severity: "MEDIUM",
      evidence: "message=urgent",
    },
  ],
  recommendation:
    "Minta klarifikasi tertulis dan jangan kirim sampel sebelum kontrak atau PO awal disepakati.",
};

@ApiTags("Fraud Detection")
@Controller("fraud")
export class FraudController {
  constructor(private readonly fraud: FraudDetectionService) {}

  @Post("scan")
  @ApiBody({
    type: FraudScanDto,
    examples: { default: { value: fraudScanExample } },
  })
  @ApiOkResponse({ schema: { example: fraudScanResponseExample } })
  scan(@Body() dto: FraudScanDto) {
    return this.fraud.scan(dto.buyerId, dto.termsText, dto.contractText);
  }

  @Post("check-red-flag")
  @ApiOperation({
    summary: "Check buyer red flags from profile and communication history",
  })
  @ApiBody({
    type: CheckRedFlagDto,
    examples: { default: { value: checkRedFlagExample } },
  })
  @ApiOkResponse({
    type: CheckRedFlagResponseDto,
    schema: { example: checkRedFlagResponseExample },
  })
  checkRedFlag(@Body() dto: CheckRedFlagDto) {
    return this.fraud.assessBuyerRisk(dto);
  }
}
