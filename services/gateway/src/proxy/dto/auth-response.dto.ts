import { ApiProperty } from "@nestjs/swagger";

export class AuthUserDto {
  @ApiProperty({ format: "uuid", example: "550e8400-e29b-41d4-a716-446655440000" })
  id!: string;

  @ApiProperty({ format: "email", example: "owner@kopigayo.id" })
  email!: string;

  @ApiProperty({ example: "premium", enum: ["free", "premium"] })
  tier!: string;
}

export class AuthResponseDto {
  @ApiProperty({ description: "Short-lived JWT — use in Authorization: Bearer header" })
  accessToken!: string;

  @ApiProperty({ description: "Long-lived refresh token (14 days)" })
  refreshToken!: string;

  @ApiProperty({ type: AuthUserDto })
  user!: AuthUserDto;
}
