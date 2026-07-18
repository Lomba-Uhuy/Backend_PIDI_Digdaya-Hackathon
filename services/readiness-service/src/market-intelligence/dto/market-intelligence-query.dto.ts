import { ApiPropertyOptional } from "@nestjs/swagger";
import { IsOptional, IsString, MaxLength, MinLength } from "class-validator";

export class MarketIntelligenceQueryDto {
  @ApiPropertyOptional({
    example: "090111",
    description: "HS Code (2 to 6 digits) for filtering trade flows",
  })
  @IsString()
  @MinLength(2)
  @MaxLength(10)
  @IsOptional()
  hsCode?: string;

  @ApiPropertyOptional({
    example: "global",
    description: "Target region or country code (ISO-2/3) or 'global'",
  })
  @IsString()
  @IsOptional()
  region?: string;
}
