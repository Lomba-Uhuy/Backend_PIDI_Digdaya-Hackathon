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
import {
  CheckRedFlagDto,
  CheckRedFlagResponseDto,
} from "./dto/check-red-flag.dto.js";
import { PricingDto } from "./dto/pricing.dto.js";
import { VerifyNibDto } from "./dto/verify-nib.dto.js";
import {
  PricingResponseDto,
  VerifyNibResponseDto,
} from "./dto/readiness-response.dto.js";
import {
  checkRedFlagExample,
  pricingExample,
  verifyNibExample,
} from "./swagger-examples.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("Deal Readiness")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller()
export class PublicReadinessProxyController {
  private readonly upstream: string;

  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("READINESS_SERVICE_URL");
  }

  @Post("calculate-price")
  @ApiOperation({ summary: "Calculate FOB / CFR / CIF export price" })
  @ApiBody({
    type: PricingDto,
    examples: { default: { value: pricingExample } },
  })
  @ApiOkResponse({ type: PricingResponseDto })
  async calculatePrice(@Body() body: PricingDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/pricing/calculate-price`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("check-red-flag")
  @ApiOperation({
    summary: "Check buyer red flags from profile and communication history",
  })
  @ApiBody({
    type: CheckRedFlagDto,
    examples: { default: { value: checkRedFlagExample } },
  })
  @ApiOkResponse({ type: CheckRedFlagResponseDto })
  async checkRedFlag(@Body() body: CheckRedFlagDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/fraud/check-red-flag`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("verify-nib")
  @ApiOperation({ summary: "Verify NIB against OSS RBA registry" })
  @ApiBody({
    type: VerifyNibDto,
    examples: { default: { value: verifyNibExample } },
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
}
