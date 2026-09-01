from django import forms

from predictions.models import Category


class CreatePredictionForm(forms.Form):
    title = forms.CharField(min_length=5, max_length=200, label="質問")
    description = forms.CharField(min_length=10, max_length=5000, widget=forms.Textarea, label="詳細説明")
    category = forms.ChoiceField(choices=Category.choices, label="カテゴリー")
    option_a = forms.CharField(max_length=50, initial="YES", label="選択肢A")
    option_b = forms.CharField(max_length=50, initial="NO", label="選択肢B")
    deadline = forms.DateTimeField(label="締切日時", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    source_url = forms.URLField(required=False, label="出典URL（任意）")
    resolution_method = forms.CharField(required=False, widget=forms.Textarea, label="結果確定方法（任意）")
    min_predictions_for_ranking = forms.IntegerField(min_value=0, initial=10, label="ランキング対象最低予測回数")


class ResolveForm(forms.Form):
    correct_option = forms.ChoiceField(choices=[("YES", "YES"), ("NO", "NO")])
