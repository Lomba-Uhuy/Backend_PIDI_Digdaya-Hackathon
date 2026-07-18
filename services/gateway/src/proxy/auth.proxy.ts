import { HttpService } from "@nestjs/axios";
import { Body, Controller, HttpCode, Post, Req } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import {
  ApiBody,
  ApiConflictResponse,
  ApiCreatedResponse,
  ApiOkResponse,
  ApiOperation,
  ApiTags,
  ApiUnauthorizedResponse,
} from "@nestjs/swagger";
import { firstValueFrom } from "rxjs";
import { AuthLoginDto } from "./dto/auth-login.dto.js";
import { AuthRegisterDto } from "./dto/auth-register.dto.js";
import { AuthResponseDto } from "./dto/auth-response.dto.js";
import { authLoginExample, authRegisterExample } from "./swagger-examples.js";
import { translateAxiosError } from "./proxy.helper.js";

@ApiTags("Authentication")
@Controller("auth")
export class AuthProxyController {
  private readonly upstream: string;

  constructor(
    private readonly http: HttpService,
    cfg: ConfigService,
  ) {
    this.upstream = cfg.getOrThrow<string>("USER_SERVICE_URL");
  }

  @Post("register")
  @HttpCode(201)
  @ApiOperation({
    summary: "Register a new user account",
    description:
      "Creates a new UMKM owner account. Returns `accessToken` and `refreshToken` immediately — no separate login step needed.",
  })
  @ApiBody({
    type: AuthRegisterDto,
    examples: { default: { value: authRegisterExample } },
  })
  @ApiCreatedResponse({
    description: "Account created — JWT pair returned",
    type: AuthResponseDto,
  })
  @ApiConflictResponse({ description: "Email already registered (HTTP 409)" })
  async register(@Body() body: AuthRegisterDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/auth/register`, body, {
          headers: {
            "x-request-id":
              (req.headers["x-request-id"] as string) ?? crypto.randomUUID(),
            "content-type": "application/json",
          },
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }

  @Post("login")
  @HttpCode(200)
  @ApiOperation({
    summary: "Log in with email + password",
    description:
      "Authenticates an existing user. Copy the `accessToken` from the response, then click **Authorize** (🔒) at the top of this page and paste it to unlock all protected endpoints.",
  })
  @ApiBody({
    type: AuthLoginDto,
    examples: { default: { value: authLoginExample } },
  })
  @ApiOkResponse({
    description: "JWT pair issued",
    type: AuthResponseDto,
  })
  @ApiUnauthorizedResponse({ description: "Invalid email or password (HTTP 401)" })
  async login(@Body() body: AuthLoginDto, @Req() req: any) {
    try {
      const { data } = await firstValueFrom(
        this.http.post(`${this.upstream}/auth/login`, body, {
          headers: {
            "x-request-id":
              (req.headers["x-request-id"] as string) ?? crypto.randomUUID(),
            "content-type": "application/json",
          },
        }),
      );
      return data;
    } catch (e) {
      translateAxiosError(e);
    }
  }
}
