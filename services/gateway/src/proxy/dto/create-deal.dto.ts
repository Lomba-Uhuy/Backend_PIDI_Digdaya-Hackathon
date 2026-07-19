import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import {
  IsIn, IsNumber, IsOptional, IsString, IsUUID, Length, Min,
} from 'class-validator';

export const DEAL_STATUSES = [
  'contacted',
  'negotiating',
  'compliance',
  'po_sent',
  'po_signed',
  'closed',
] as const;

export class CreateDealDto {
  @ApiPropertyOptional({ format: 'uuid', description: 'Product the deal is about' })
  @IsOptional()
  @IsUUID()
  productId?: string;

  @ApiPropertyOptional({ description: 'Buyer id (if a real registered buyer)' })
  @IsOptional()
  @IsString()
  buyerId?: string;

  @ApiProperty({ example: 'GlobalTech Imports GmbH' })
  @IsString()
  @Length(1, 255)
  buyerName!: string;

  @ApiPropertyOptional({ example: 'Germany' })
  @IsOptional()
  @IsString()
  @Length(1, 64)
  buyerCountry?: string;

  @ApiPropertyOptional({ enum: DEAL_STATUSES, default: 'contacted' })
  @IsOptional()
  @IsIn(DEAL_STATUSES)
  status?: (typeof DEAL_STATUSES)[number];

  @ApiPropertyOptional({ example: 2.75, minimum: 0 })
  @IsOptional()
  @IsNumber()
  @Min(0)
  agreedPrice?: number;

  @ApiPropertyOptional({ example: 'Kami mengajukan penawaran harga sebesar $2.75/kg.' })
  @IsOptional()
  @IsString()
  lastMessage?: string;
}
