import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import {
  IsOptional,
  IsString,
  IsUUID,
  MaxLength,
  MinLength,
} from "class-validator";

export class FraudScanDto {
  @ApiProperty({ example: "2c2d2c1b-5a7d-4d25-8bc3-e0bf7f2f2d11" })
  @IsUUID()
  buyerId!: string;

  @ApiProperty({
    example:
      "Payment must be made in full by wire transfer. Please ignore the invoice if the amount is overpaid.",
    maxLength: 20000,
  })
  @IsString()
  @MinLength(1)
  @MaxLength(20_000)
  termsText!: string;

  @ApiPropertyOptional({
    example:
      "Goods will be shipped to a third-party warehouse before bank clearance is completed.",
    maxLength: 50000,
  })
  @IsString()
  @MaxLength(50_000)
  @IsOptional()
  contractText?: string;
}
