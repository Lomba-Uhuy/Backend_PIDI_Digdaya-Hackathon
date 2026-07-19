import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional, IsString, MinLength } from 'class-validator';

export class NegotiationDraftDto {
  @ApiProperty({
    example:
      'Kami tertarik dengan kopi Gayo Anda. Bisakah Anda memberikan quotation untuk 500kg kopi roasted whole bean?',
  })
  @IsString()
  @MinLength(10)
  inquiry_text!: string;

  @ApiProperty({ example: '5d9f2d9e-0f0f-4cb0-9d84-1d7a9ef5d8d7' })
  @IsString()
  product_id!: string;

  @ApiPropertyOptional({ example: '2c2d2c1b-5a7d-4d25-8bc3-e0bf7f2f2d11' })
  @IsString()
  @IsOptional()
  buyer_id?: string;
}
