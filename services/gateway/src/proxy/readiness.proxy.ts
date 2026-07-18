import { HttpService } from "@nestjs/axios";
import { Body, Controller, Post, Req, UseGuards } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import {
  ApiBearerAuth,
  ApiBody,
  ApiOkResponse,
  ApiOperation,
  ApiTags,
} from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { FraudScanDto } from "./dto/fraud-scan.dto.js";
import { PricingDto } from "./dto/pricing.dto.js";
import { VerifyNibDto } from "./dto/verify-nib.dto.js";
import { MarketIntelligenceQueryDto } from "./dto/market-intelligence-query.dto.js";
import {
  FraudScanResponseDto,
  PricingResponseDto,
  VerifyNibResponseDto,
} from "./dto/readiness-response.dto.js";
import { fraudScanExample, pricingExample } from "./swagger-examples.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("Deal Readiness")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("readiness")
export class ReadinessProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("READINESS_SERVICE_URL");
  }

  @Post("pricing")
  @ApiOperation({
    summary: "Calculate FOB / CIF export price",
    description:
      "Computes FOB, CFR, and CIF price breakdowns from HPP + logistics inputs.",
  })
  @ApiBody({
    type: PricingDto,
    examples: { default: { value: pricingExample } },
  })
  @ApiOkResponse({ type: PricingResponseDto })
  async pricing(@Body() body: PricingDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/pricing/calculate`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("fraud-scan")
  @ApiOperation({
    summary: "Scan buyer contract / terms for fraud red flags",
    description:
      "Analyses payment terms and contract text against ICC red flag catalogue. Returns risk level (GREEN / YELLOW / RED) with flagged excerpts.",
  })
  @ApiBody({
    type: FraudScanDto,
    examples: { default: { value: fraudScanExample } },
  })
  @ApiOkResponse({ type: FraudScanResponseDto })
  async fraudScan(@Body() body: FraudScanDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/fraud/scan`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("verify-nib")
  @ApiOperation({
    summary: "Verify NIB against OSS RBA registry",
    description:
      "Validates a 10-15 digit NIB (Nomor Induk Berusaha) against the Indonesian OSS RBA system. `sandbox_mode: true` means OSS was unreachable and the result is simulated.",
  })
  @ApiBody({
    type: VerifyNibDto,
    examples: { default: { value: { nib: "1234567890" } } },
  })
  @ApiOkResponse({ type: VerifyNibResponseDto })
  async verifyNib(@Body() body: VerifyNibDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/nib/verify`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("market-intelligence")
  @ApiOperation({
    summary: "Get global market intelligence and stats",
    description: "Queries BPS and UN Comtrade records for export/import stats and generates AI opportunities.",
  })
  @ApiBody({ type: MarketIntelligenceQueryDto })
  async marketIntelligence(@Body() body: MarketIntelligenceQueryDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/market-intelligence/stats`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
