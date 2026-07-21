import { HttpService } from "@nestjs/axios";
import {
  Body, Controller, Get, HttpCode, Param, Patch, Post, Query, Req, UseGuards,
} from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { ApiBearerAuth, ApiOperation, ApiTags } from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { CreateDealDto } from "./dto/create-deal.dto.js";
import { UpdateDealDto } from "./dto/update-deal.dto.js";
import { CreateMessageDto } from "./dto/create-message.dto.js";
import { BuyerReplyDto } from "./dto/buyer-reply.dto.js";
import { SignPoDto } from "./dto/sign-po.dto.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("Deals")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("deals")
export class DealProxyController {
  private readonly upstream: string;
  private readonly commsUpstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
    this.commsUpstream = cfg.getOrThrow<string>("COMMS_SERVICE_URL");
  }

  @Post()
  @HttpCode(201)
  @ApiOperation({ summary: "Create a deal for the caller UMKM" })
  async create(@Body() body: CreateDealDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/deals`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get()
  @ApiOperation({ summary: "List deals (paginated) for the caller UMKM" })
  async list(
    @Req() req: any,
    @Query("status") status?: string,
    @Query("page") page?: string,
    @Query("pageSize") pageSize?: string,
  ) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/deals`, {
          headers: buildForwardHeaders(req),
          params: { status, page, pageSize },
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get("analytics")
  @ApiOperation({ summary: "Negotiation analytics (conversion, pipeline, distributions)" })
  async analytics(@Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/deals/analytics`, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get(":id")
  @ApiOperation({ summary: "Get a single deal" })
  async findOne(@Param("id") id: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/deals/${id}`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Patch(":id")
  @ApiOperation({ summary: "Update a deal (status / agreed price / last message)" })
  async update(@Param("id") id: string, @Body() body: UpdateDealDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.patch(`${this.upstream}/deals/${id}`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  // ── Negotiation thread (deal messages) ─────────────────────────────────────
  @Get(":id/messages")
  @ApiOperation({ summary: "List messages for a deal (oldest first)" })
  async listMessages(@Param("id") id: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/deals/${id}/messages`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post(":id/messages")
  @HttpCode(201)
  @ApiOperation({ summary: "Append a message to a deal" })
  async createMessage(@Param("id") id: string, @Body() body: CreateMessageDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/deals/${id}/messages`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post(":id/messages/buyer-reply")
  @HttpCode(201)
  @ApiOperation({
    summary: "Generate + persist an AI-simulated buyer reply (converges to a real price)",
    description:
      "Orchestrates: load deal + thread → comms-service simulate-buyer-reply (deterministic numeric negotiation anchored to the seller's CIF + real BPS benchmark) → persist the buyer turn → auto-advance the deal to 'compliance' with the agreed price on acceptance.",
  })
  async buyerReply(@Param("id") id: string, @Body() body: BuyerReplyDto, @Req() req: any) {
    const headers = buildForwardHeaders(req);
    try {
      const [{ data: deal }, { data: msgs }] = await Promise.all([
        firstValueFrom(this.http.get(`${this.upstream}/deals/${id}`, { headers })),
        firstValueFrom(this.http.get(`${this.upstream}/deals/${id}/messages`, { headers })),
      ]);

      const history = ((msgs?.items ?? []) as Array<{ sender: string; text: string }>).map(
        (m) => ({ sender: m.sender, text: m.text }),
      );

      const { data: sim } = await firstValueFrom(
        this.http.post(
          `${this.commsUpstream}/api/v1/negotiations/simulate-buyer-reply`,
          {
            history,
            product_name: body.productName,
            hs_code: body.hsCode,
            buyer_name: deal?.buyerName,
            buyer_country: deal?.buyerCountry,
            seller_price: body.sellerPrice,
            floor_price: body.floorPrice,
            benchmark_unit_value: body.benchmarkUnitValue,
          },
          { headers },
        ),
      );

      const { data: message } = await firstValueFrom(
        this.http.post(
          `${this.upstream}/deals/${id}/messages`,
          { text: sim.text, sender: "buyer", intent: sim.intent },
          { headers },
        ),
      );

      let dealStatus = deal?.status;
      if (sim.accept && sim.agreed_price != null) {
        const { data: updated } = await firstValueFrom(
          this.http.patch(
            `${this.upstream}/deals/${id}`,
            { status: "compliance", agreedPrice: sim.agreed_price },
            { headers },
          ),
        );
        dealStatus = updated?.status;
      }

      return {
        message,
        accept: sim.accept,
        agreedPrice: sim.agreed_price,
        proposedPrice: sim.proposed_price,
        intent: sim.intent,
        dealStatus,
      };
    } catch (e) {
      translateAxiosError(e);
    }
  }

  // ── Purchase order ─────────────────────────────────────────────────────────
  @Post(":id/purchase-order")
  @ApiOperation({ summary: "Generate (once) a PO from the deal + product" })
  async generatePo(@Param("id") id: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/deals/${id}/purchase-order`, {}, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Get(":id/purchase-order")
  @ApiOperation({ summary: "Get the deal purchase order" })
  async getPo(@Param("id") id: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/deals/${id}/purchase-order`, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post(":id/purchase-order/send")
  @ApiOperation({ summary: "Mark PO as sent (advances deal to po_sent)" })
  async sendPo(@Param("id") id: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/deals/${id}/purchase-order/send`, {}, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post(":id/purchase-order/sign")
  @ApiOperation({ summary: "Sign the PO (advances deal to po_signed)" })
  async signPo(@Param("id") id: string, @Body() body: SignPoDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/deals/${id}/purchase-order/sign`, body, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  // ── Compliance ─────────────────────────────────────────────────────────────
  @Get(":id/compliance")
  @ApiOperation({ summary: "List compliance checks for a deal" })
  async getCompliance(@Param("id") id: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/deals/${id}/compliance`, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post(":id/compliance/run")
  @ApiOperation({ summary: "Run/refresh compliance checks from real deal + product data" })
  async runCompliance(@Param("id") id: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/deals/${id}/compliance/run`, {}, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
