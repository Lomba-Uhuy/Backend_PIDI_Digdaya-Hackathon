import { Body, Controller, Post } from "@nestjs/common";
import { ApiBody, ApiOkResponse, ApiProperty, ApiTags } from "@nestjs/swagger";
import { IsEmail, IsString, MinLength } from "class-validator";
import { AuthService } from "./auth.service.js";

class CredentialsDto {
  @ApiProperty({ example: "owner@kopigayo.id", format: "email" })
  @IsEmail()
  email!: string;

  @ApiProperty({ example: "KopiGayo!2026", minLength: 8 })
  @IsString()
  @MinLength(8)
  password!: string;
}

class RefreshDto {
  @ApiProperty({ description: "A valid refresh token from login/register" })
  @IsString()
  @MinLength(20)
  refreshToken!: string;
}

const authResponseExample = {
  accessToken: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  refreshToken: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  user: {
    id: "550e8400-e29b-41d4-a716-446655440000",
    email: "owner@kopigayo.id",
    tier: "premium",
  },
};

const authLoginExample = {
  email: "owner@kopigayo.id",
  password: "KopiGayo!2026",
};

@ApiTags("Auth")
@Controller("auth")
export class AuthController {
  constructor(private readonly auth: AuthService) {}

  @Post("register")
  @ApiBody({
    type: CredentialsDto,
    examples: { default: { value: authLoginExample } },
  })
  @ApiOkResponse({ schema: { example: authResponseExample } })
  register(@Body() body: CredentialsDto) {
    return this.auth.register(body.email, body.password);
  }

  @Post("login")
  @ApiBody({
    type: CredentialsDto,
    examples: { default: { value: authLoginExample } },
  })
  @ApiOkResponse({ schema: { example: authResponseExample } })
  login(@Body() body: CredentialsDto) {
    return this.auth.login(body.email, body.password);
  }

  @Post("refresh")
  @ApiBody({ type: RefreshDto })
  @ApiOkResponse({ schema: { example: authResponseExample } })
  refresh(@Body() body: RefreshDto) {
    return this.auth.refresh(body.refreshToken);
  }
}
