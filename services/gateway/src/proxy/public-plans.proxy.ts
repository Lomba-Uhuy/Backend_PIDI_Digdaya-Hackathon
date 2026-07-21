import { HttpService } from "@nestjs/axios";
import { Controller, Get } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { ApiOperation, ApiTags } from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { translateAxiosError } from "./proxy.helper.js";

/**
 * PUBLIC plan catalogue — no authentication. The landing page renders pricing
 * from this endpoint so plan limits always originate from backend feature flags
 * (never hardcoded in the frontend).
 */
@ApiTags("Subscription")
@Controller("subscription")
export class PublicPlansProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
  }

  @Get("plans")
  @ApiOperation({ summary: "Public plan catalogue (labels, quotas, feature flags)" })
  async plans() {
    try {
      const { data } = await firstValueFrom(this.http.get(`${this.upstream}/subscription/plans`));
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
