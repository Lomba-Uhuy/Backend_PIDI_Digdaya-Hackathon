import { ApiPropertyOptional } from "@nestjs/swagger";
import { IsNumber, IsOptional, IsString, Length, Min } from "class-validator";

/** Context the frontend supplies so the AI counterparty negotiates against real numbers. */
export class BuyerReplyDto {
  @ApiPropertyOptional({ description: "Latest CIF/unit the seller proposed (USD/kg)" })
  @IsOptional()
  @IsNumber()
  @Min(0)
  sellerPrice?: number;

  @ApiPropertyOptional({ description: "Seller floor price (USD/kg)" })
  @IsOptional()
  @IsNumber()
  @Min(0)
  floorPrice?: number;

  @ApiPropertyOptional({ description: "Real BPS export unit value (USD/kg)" })
  @IsOptional()
  @IsNumber()
  @Min(0)
  benchmarkUnitValue?: number;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @Length(1, 255)
  productName?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @Length(1, 16)
  hsCode?: string;
}
