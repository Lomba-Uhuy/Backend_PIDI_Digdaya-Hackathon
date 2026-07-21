-- Idempotent: this migration captures schema (deal lifecycle, product HS
-- classification columns, and the product initialization workflow engine) that
-- was applied out-of-band on existing dev DBs. Guards make it safe to run on
-- both a fresh database and one where these objects already exist.
DO $$ BEGIN CREATE TYPE "public"."deal_status" AS ENUM('contacted', 'negotiating', 'compliance', 'po_sent', 'po_signed', 'closed'); EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN CREATE TYPE "public"."deal_message_sender" AS ENUM('umkm', 'buyer', 'system'); EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN CREATE TYPE "public"."workflow_stage_status" AS ENUM('queued', 'running', 'completed', 'failed', 'retrying', 'skipped'); EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN CREATE TYPE "public"."workflow_status" AS ENUM('queued', 'running', 'completed', 'failed'); EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN CREATE TYPE "public"."po_status" AS ENUM('draft', 'sent', 'signed'); EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN CREATE TYPE "public"."compliance_kind" AS ENUM('nib', 'fraud_scan', 'document'); EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN CREATE TYPE "public"."compliance_status" AS ENUM('pass', 'warn', 'fail'); EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "deal" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"umkm_id" uuid NOT NULL,
	"product_id" uuid,
	"buyer_id" uuid,
	"buyer_name" varchar(255),
	"buyer_country" varchar(64),
	"status" "deal_status" DEFAULT 'contacted' NOT NULL,
	"agreed_price" numeric(12, 4),
	"last_message" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "deal_message" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"deal_id" uuid NOT NULL,
	"sender" "deal_message_sender" NOT NULL,
	"text" text NOT NULL,
	"intent" varchar(32),
	"meta" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "product_workflow" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"product_id" uuid NOT NULL,
	"umkm_id" uuid NOT NULL,
	"workflow_type" varchar(48) DEFAULT 'product_initialization' NOT NULL,
	"status" "workflow_status" DEFAULT 'queued' NOT NULL,
	"current_stage" varchar(48),
	"retry_count" integer DEFAULT 0 NOT NULL,
	"failure_reason" text,
	"current_worker" varchar(64),
	"execution_version" integer DEFAULT 1 NOT NULL,
	"started_at" timestamp with time zone,
	"finished_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "product_workflow_product_id_unique" UNIQUE("product_id")
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "workflow_event" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"workflow_id" uuid NOT NULL,
	"type" varchar(48) NOT NULL,
	"stage_name" varchar(48),
	"message" text,
	"metadata" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "workflow_stage" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"workflow_id" uuid NOT NULL,
	"stage_name" varchar(48) NOT NULL,
	"sequence" integer NOT NULL,
	"status" "workflow_stage_status" DEFAULT 'queued' NOT NULL,
	"worker_name" varchar(64),
	"job_id" varchar(128),
	"retry_count" integer DEFAULT 0 NOT NULL,
	"duration_ms" integer,
	"error_message" text,
	"metadata" jsonb,
	"started_at" timestamp with time zone,
	"finished_at" timestamp with time zone
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "purchase_order" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"deal_id" uuid NOT NULL,
	"po_number" varchar(40) NOT NULL,
	"product_id" uuid,
	"product_name" varchar(255),
	"buyer_name" varchar(255),
	"buyer_country" varchar(64),
	"incoterm" varchar(16) DEFAULT 'CIF' NOT NULL,
	"unit_price" numeric(18, 4) NOT NULL,
	"qty" integer DEFAULT 1 NOT NULL,
	"currency" varchar(8) DEFAULT 'USD' NOT NULL,
	"subtotal" numeric(18, 4) NOT NULL,
	"payment_terms" varchar(255) DEFAULT '30% DP / 70% L/C' NOT NULL,
	"status" "po_status" DEFAULT 'draft' NOT NULL,
	"signed_by" varchar(255),
	"signature" text,
	"signed_at" timestamp with time zone,
	"terms" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "purchase_order_deal_id_unique" UNIQUE("deal_id")
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "compliance_check" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"deal_id" uuid NOT NULL,
	"kind" "compliance_kind" NOT NULL,
	"label" varchar(160) NOT NULL,
	"status" "compliance_status" NOT NULL,
	"detail" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "reminder" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid NOT NULL,
	"title" varchar(255) NOT NULL,
	"remind_at" timestamp with time zone NOT NULL,
	"type" varchar(64) DEFAULT 'general' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "product" ADD COLUMN IF NOT EXISTS "hs_candidates" jsonb DEFAULT '[]'::jsonb NOT NULL;--> statement-breakpoint
ALTER TABLE "product" ADD COLUMN IF NOT EXISTS "hs_model_version" varchar(64);--> statement-breakpoint
ALTER TABLE "product" ADD COLUMN IF NOT EXISTS "hs_classified_at" timestamp with time zone;--> statement-breakpoint
DO $$ BEGIN ALTER TABLE "deal" ADD CONSTRAINT "deal_umkm_id_umkm_id_fk" FOREIGN KEY ("umkm_id") REFERENCES "public"."umkm"("id") ON DELETE cascade ON UPDATE no action; EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN ALTER TABLE "deal" ADD CONSTRAINT "deal_product_id_product_id_fk" FOREIGN KEY ("product_id") REFERENCES "public"."product"("id") ON DELETE set null ON UPDATE no action; EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN ALTER TABLE "deal_message" ADD CONSTRAINT "deal_message_deal_id_deal_id_fk" FOREIGN KEY ("deal_id") REFERENCES "public"."deal"("id") ON DELETE cascade ON UPDATE no action; EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN ALTER TABLE "product_workflow" ADD CONSTRAINT "product_workflow_product_id_product_id_fk" FOREIGN KEY ("product_id") REFERENCES "public"."product"("id") ON DELETE cascade ON UPDATE no action; EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN ALTER TABLE "workflow_event" ADD CONSTRAINT "workflow_event_workflow_id_product_workflow_id_fk" FOREIGN KEY ("workflow_id") REFERENCES "public"."product_workflow"("id") ON DELETE cascade ON UPDATE no action; EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN ALTER TABLE "workflow_stage" ADD CONSTRAINT "workflow_stage_workflow_id_product_workflow_id_fk" FOREIGN KEY ("workflow_id") REFERENCES "public"."product_workflow"("id") ON DELETE cascade ON UPDATE no action; EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN ALTER TABLE "purchase_order" ADD CONSTRAINT "purchase_order_deal_id_deal_id_fk" FOREIGN KEY ("deal_id") REFERENCES "public"."deal"("id") ON DELETE cascade ON UPDATE no action; EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN ALTER TABLE "compliance_check" ADD CONSTRAINT "compliance_check_deal_id_deal_id_fk" FOREIGN KEY ("deal_id") REFERENCES "public"."deal"("id") ON DELETE cascade ON UPDATE no action; EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
DO $$ BEGIN ALTER TABLE "reminder" ADD CONSTRAINT "reminder_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE cascade ON UPDATE no action; EXCEPTION WHEN duplicate_object THEN null; END $$;--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "deal_umkm_status_idx" ON "deal" USING btree ("umkm_id","status");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "deal_message_deal_created_idx" ON "deal_message" USING btree ("deal_id","created_at");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "workflow_event_wf_idx" ON "workflow_event" USING btree ("workflow_id","created_at");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "workflow_stage_wf_idx" ON "workflow_stage" USING btree ("workflow_id","sequence");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "compliance_check_deal_idx" ON "compliance_check" USING btree ("deal_id","created_at");--> statement-breakpoint
CREATE INDEX IF NOT EXISTS "reminder_user_idx" ON "reminder" USING btree ("user_id","remind_at");