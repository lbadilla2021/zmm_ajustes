/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";

patch(ViewButton.prototype, {
    async onClick(ev) {
        if (this._barcaShouldSaveBeforeStart()) {
            ev.stopPropagation();
            ev.preventDefault();
            const runtime = this._barcaGetStartRuntime();
            const saved = await this._barcaSaveWorkorderBeforeStart(runtime);
            if (!saved) {
                return;
            }
            const lineId = this._barcaResolveSavedWorkorderLineId(runtime);
            if (!lineId) {
                this.env.services.notification.add(
                    "No se pudo identificar la actividad guardada. Intente nuevamente.",
                    { type: "warning" }
                );
                return;
            }
            await this._barcaStartWorkorderLine(runtime, lineId);
            return;
        }
        return super.onClick(ev);
    },

    _barcaShouldSaveBeforeStart() {
        const { name, type } = this.clickParams;
        return (
            type === "object" &&
            name === "action_start_line" &&
            this.props.record?.resModel === "barca.maintenance.workorder.line"
        );
    },

    _barcaGetStartRuntime() {
        const record = this.props.record;
        return {
            record,
            root: record?.model?.root,
            orm: record?.model?.orm || this.env.services.orm,
            resModel: record?.resModel,
            context: record?.context,
        };
    },

    _barcaGetMany2OneId(value) {
        return Array.isArray(value) ? value[0] : value || false;
    },

    _barcaGetLineSignature(record = this.props.record) {
        const data = record?.data || {};
        return {
            id: typeof record?.resId === "number" ? record.resId : false,
            sequence: data.sequence || false,
            technicalLocationId: this._barcaGetMany2OneId(data.technical_location_id),
            interventionTypeId: this._barcaGetMany2OneId(data.intervention_type_id),
            activityId: this._barcaGetMany2OneId(data.activity_id),
        };
    },

    async _barcaSaveWorkorderBeforeStart(runtime) {
        const { record, root } = runtime;
        if (!root?.save) {
            return true;
        }

        const proms = [];
        record.model.bus.trigger("NEED_LOCAL_CHANGES", { proms });
        await Promise.all(proms);
        if (record._updatePromise) {
            await record._updatePromise;
        }

        const list = record._parent;
        if (list?.leaveEditMode) {
            const canProceed = await list.leaveEditMode({
                canAbandon: false,
                validate: true,
            });
            if (!canProceed) {
                return false;
            }
        }
        if (root.leaveEditMode) {
            const canProceed = await root.leaveEditMode({
                canAbandon: false,
                validate: true,
            });
            if (!canProceed) {
                return false;
            }
        }

        this._barcaStartLineSignature = this._barcaGetLineSignature(record);
        const saved = await root.save({ reload: false });
        if (saved && root.load) {
            await root.load();
        }
        return saved;
    },

    _barcaResolveSavedWorkorderLineId(runtime) {
        const signature = this._barcaStartLineSignature;
        if (!signature) {
            return false;
        }
        if (signature.id) {
            return signature.id;
        }

        const lines = runtime.root?.data?.barca_activity_line_ids?.records || [];
        const candidates = lines.filter((line) => {
            const data = line.data || {};
            return (
                typeof line.resId === "number" &&
                data.state === "pending" &&
                this._barcaGetMany2OneId(data.technical_location_id) ===
                    signature.technicalLocationId &&
                this._barcaGetMany2OneId(data.intervention_type_id) ===
                    signature.interventionTypeId &&
                this._barcaGetMany2OneId(data.activity_id) === signature.activityId &&
                (!signature.sequence || data.sequence === signature.sequence)
            );
        });
        return candidates.at(-1)?.resId || false;
    },

    async _barcaStartWorkorderLine(runtime, lineId) {
        await runtime.orm.call(runtime.resModel, "action_start_line", [[lineId]], {
            context: runtime.context,
        });
        await runtime.root.load();
    },
});
