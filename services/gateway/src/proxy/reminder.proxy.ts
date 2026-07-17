import { HttpService } from "@nestjs/axios";
import {
  Body, Controller, Delete, Get, HttpCode, Param, Post, Req, UseGuards,
} from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { ApiBearerAuth, ApiOperation, ApiTags } from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { JwtAuthGuard } from "../auth/guards/jwt-auth.guard.js";
import { CreateReminderDto } from "./dto/create-reminder.dto.js";
import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";

@ApiTags("Reminders")
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller("reminders")
export class ReminderProxyController {
  private readonly upstream: string;
  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
  }

  @Get()
  @ApiOperation({ summary: "List reminders for the caller" })
  async list(@Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/reminders`, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post()
  @HttpCode(201)
  @ApiOperation({ summary: "Create a reminder" })
  async create(@Body() body: CreateReminderDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/reminders`, body, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Delete(":id")
  @ApiOperation({ summary: "Delete a reminder" })
  async remove(@Param("id") id: string, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.delete(`${this.upstream}/reminders/${id}`, { headers: buildForwardHeaders(req) }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
