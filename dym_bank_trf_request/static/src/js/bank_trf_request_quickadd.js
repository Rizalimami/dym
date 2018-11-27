openerp.dym_bank_trf_request = function (instance) {
    openerp.dym_bank_trf_request.quickadd(instance);
};

openerp.dym_bank_trf_request.quickadd = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;
    
    instance.web.dym_bank_trf_request = instance.web.dym_bank_trf_request || {};

    instance.web.views.add('tree_bank_trf_request_quickadd', 'instance.web.dym_bank_trf_request.QuickAddListView');
    instance.web.dym_bank_trf_request.QuickAddListView = instance.web.ListView.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.branches = [];
            this.dates_due = [];
            this.current_branch = null;
            this.current_date_due = null;
            this.default_date_due = null;
            this.default_branch = null;
        },
        start:function(){
            var tmp = this._super.apply(this, arguments);
            var self = this;
            var defs = [];
            this.$el.parent().prepend(QWeb.render("BankTransferRequestQuickAdd", {widget: this}));
            
            this.$el.parent().find('.oe_bank_trf_request_select_branch').change(function() {
                    self.current_branch = this.value === '' ? null : parseInt(this.value);
                    self.do_search(self.last_domain, self.last_context, self.last_group_by);
                });
            this.$el.parent().find('.oe_bank_trf_request_select_date_due').change(function() {
                    self.current_date_due = this.value === '' ? null : this.value;
                    self.do_search(self.last_domain, self.last_context, self.last_group_by);
                });
            this.on('edit:after', this, function () {
                self.$el.parent().find('.oe_bank_trf_request_select_branch').attr('disabled', 'disabled');
                self.$el.parent().find('.oe_bank_trf_request_select_date_due').attr('disabled', 'disabled');
            });
            this.on('save:after cancel:after', this, function () {
                self.$el.parent().find('.oe_bank_trf_request_select_branch').removeAttr('disabled');
                self.$el.parent().find('.oe_bank_trf_request_select_date_due').removeAttr('disabled');
            });
            var mod = new instance.web.Model("bank.trf.request", self.dataset.context, self.dataset.domain);
            defs.push(mod.call("default_get", [['branch_id','date_due'],self.dataset.context]).then(function(result) {
                self.current_date_due = result['date_due'];
                self.current_branch = result['branch_id'];
            }));
            defs.push(mod.call("list_branches", []).then(function(result) {
                self.branches = result;
            }));
            defs.push(mod.call("list_dates_due", []).then(function(result) {
                self.dates_due = result;
            }));
            return $.when(tmp, defs);
        },
        do_search: function(domain, context, group_by) {
            var self = this;
            this.last_domain = domain;
            this.last_context = context;
            this.last_group_by = group_by;
            this.old_search = _.bind(this._super, this);
            var o;
            self.$el.parent().find('.oe_bank_trf_request_select_branch').children().remove().end();
            self.$el.parent().find('.oe_bank_trf_request_select_branch').append(new Option('', ''));
            for (var i = 0;i < self.branches.length;i++){
                o = new Option(self.branches[i][1], self.branches[i][0]);
                if (self.branches[i][0] === self.current_branch){
                    $(o).attr('selected',true);
                }
                self.$el.parent().find('.oe_bank_trf_request_select_branch').append(o);
            }
            self.$el.parent().find('.oe_bank_trf_request_select_date_due').children().remove().end();
            self.$el.parent().find('.oe_bank_trf_request_select_date_due').append(new Option('', ''));
            for (var i = 0;i < self.dates_due.length;i++){
                o = new Option(self.dates_due[i][1], self.dates_due[i][0]);
                self.$el.parent().find('.oe_bank_trf_request_select_date_due').append(o);
            }    
            self.$el.parent().find('.oe_bank_trf_request_select_date_due').val(self.current_date_due).attr('selected',true);
            return self.search_by_branch_date();
        },
        search_by_branch_date: function() {
            var self = this;
            var domain = [];
            if (self.current_branch !== null) domain.push(["branch_id", "=", self.current_branch]);
            if (self.current_date_due !== null) domain.push(["date_due", "=", self.current_date_due]);
            self.last_context["branch_id"] = self.current_branch === null ? false : self.current_branch;
            if (self.current_date_due === null) delete self.last_context["date_due"];
            else self.last_context["date_due"] =  self.current_date_due;
            var compound_domain = new instance.web.CompoundDomain(self.last_domain, domain);
            self.dataset.domain = compound_domain.eval();
            return self.old_search(compound_domain, self.last_context, self.last_group_by);
        },
    });
};
