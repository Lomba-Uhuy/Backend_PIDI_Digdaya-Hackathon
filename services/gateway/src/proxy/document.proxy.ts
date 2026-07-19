import { HttpService } from "@nestjs/axios";
import { Body, Controller, Get, Post, Req } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { ApiBody, ApiOkResponse, ApiOperation, ApiTags } from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";

import { buildForwardHeaders, translateAxiosError } from "./proxy.helper.js";
import { GenerateDocsDto } from "./dto/generate-docs.dto.js";

@ApiTags("Document Checklist")
@Controller("documents")
export class DocumentProxyController {
  private readonly upstream: string;

  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("READINESS_SERVICE_URL");
  }

  @Get("checklist")
  @ApiOperation({
    summary: "Get the standard export document checklist",
    description:
      "Returns the base Indonesian export document checklist from the readiness service.",
  })
  @ApiOkResponse({
    description: "List of document checklist items",
  })
  async checklist(@Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.get(`${this.upstream}/documents/checklist`, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("generate")
  @ApiOperation({
    summary: "Generate official export documents dynamically",
    description: "Compiles custom content for commercial documents based on the active transaction details.",
  })
  @ApiBody({ type: GenerateDocsDto })
  async generate(@Body() body: GenerateDocsDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/documents/generate`, body, {
          headers: buildForwardHeaders(req),
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
