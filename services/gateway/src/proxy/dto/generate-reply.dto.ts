import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import { IsOptional, IsString, MinLength } from "class-validator";

export class GenerateReplyDto {
  @ApiProperty({
    description: "Raw email text received from the importer",
    minLength: 10,
    example: "Dear Sir, we are interested in your Gayo coffee. Could you please send us a quotation for 500kg?",
  })
  @IsString()
  @MinLength(10)
  importer_email!: string;

  @ApiProperty({
    description: "UMKM product UUID — used to load pricing context for guardrails",
    example: "5d9f2d9e-0f0f-4cb0-9d84-1d7a9ef5d8d7",
  })
  @IsString()
  product_id!: string;

  @ApiPropertyOptional({
    description: "Known buyer UUID for additional context enrichment",
    example: "2c2d2c1b-5a7d-4d25-8bc3-e0bf7f2f2d11",
  })
  @IsOptional()
  @IsString()
  buyer_id?: string;
}
