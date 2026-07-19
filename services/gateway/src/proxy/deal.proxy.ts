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
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("Deals")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("deals")
export class DealProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
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
}
